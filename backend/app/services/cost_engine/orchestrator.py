"""Orchestrateur du moteur de coût v2 (Sprint 5 manuel + Sprint 7 matching).

Instancie les 7 calculateurs, les invoque, agrège les PosteResult, calcule
cout_revient + prix_vente_ht. Branche sur `devis.mode_calcul` :
  - 'manuel'   → 1 résultat DevisOutput (Sprint 5, V1a/V1b/V1b forme spé EXACT)
  - 'matching' → 1-3 résultats DevisOutputMatching (Sprint 7, cylindres trouvés)

Le pct_marge appliqué vient de devis.pct_marge_override si fourni, sinon
de entreprise.pct_marge_defaut. Fallback 0.18 (preset Compétitif PRD).
"""
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entreprise, Machine
from app.schemas.devis import (
    CandidatCylindreOutput,
    DevisInput,
    DevisOutput,
    DevisOutputMatching,
)
from app.schemas.poste_result import PosteResult
from app.services.cost_engine.cylindre_matcher import find_cylindre_candidats
from app.services.cost_engine.errors import CostEngineError
from app.services.cost_engine.poste_1_matiere import CalculateurPoste1Matiere
from app.services.cost_engine.poste_2_encres import CalculateurPoste2Encres
from app.services.cost_engine.poste_3_cliches import (
    CalculateurPoste3ClichesOutillage,
)
from app.services.cost_engine.poste_4_calage import CalculateurPoste4Calage
from app.services.cost_engine.poste_5_roulage import CalculateurPoste5Roulage
from app.services.cost_engine.poste_6_finitions import CalculateurPoste6Finitions
from app.services.cost_engine.poste_7_mo import CalculateurPoste7MO

logger = logging.getLogger(__name__)

PCT_MARGE_FALLBACK = Decimal("0.18")  # preset Compétitif persona PRD

# Sprint 5 Lot 5c : intervalle default mode manuel = 3 mm.
# Sprint 7 Lot 7b/7d V2 : applicable seulement si devis.intervalle_mm is None
# en mode manuel (préserve V1a EXACT 1449.09 €).
INTERVALLE_ETIQUETTES_MM = Decimal("3")


class MoteurDevis:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._calculateurs = [
            CalculateurPoste1Matiere(db),
            CalculateurPoste2Encres(db),
            CalculateurPoste3ClichesOutillage(db),
            CalculateurPoste4Calage(db),
            CalculateurPoste5Roulage(db),
            CalculateurPoste6Finitions(db),
            CalculateurPoste7MO(db),
        ]

    def calculer(self, devis: DevisInput) -> DevisOutput | DevisOutputMatching:
        """Dispatch sur devis.mode_calcul (Sprint 7 Lot 7d V2)."""
        if devis.mode_calcul == "matching":
            return self._compute_matching(devis)
        return self._compute_manuel(devis)

    # -----------------------------------------------------------------------
    # Mode 'manuel' (Sprint 5/6) — V1a/V1b/V1b forme spé EXACT préservés
    # -----------------------------------------------------------------------

    def _compute_manuel(self, devis: DevisInput) -> DevisOutput:
        postes = [calc.calculer(devis) for calc in self._calculateurs]
        cout_revient = sum(
            (p.montant_eur for p in postes), Decimal(0)
        ).quantize(Decimal("0.01"))
        pct_marge = self._resolve_pct_marge(devis)
        prix_vente_ht = (cout_revient * (Decimal(1) + pct_marge)).quantize(
            Decimal("0.01")
        )
        # Sprint 7 Lot 7b : si user a saisi intervalle_mm, on l'utilise ;
        # sinon default 3 (préserve V1a Sprint 5 EXACT car payload V1a sans
        # intervalle_mm → None → 3).
        intervalle = (
            devis.intervalle_mm
            if devis.intervalle_mm is not None
            else INTERVALLE_ETIQUETTES_MM
        )
        prix_au_mille = self._compute_prix_au_mille_manuel(
            devis, prix_vente_ht, intervalle
        )

        logger.info(
            "Devis MANUEL calculé: cout_revient=%s €, marge=%s, prix_HT=%s €, prix_mille=%s €/1000 (intervalle=%s mm)",
            cout_revient, pct_marge, prix_vente_ht, prix_au_mille, intervalle,
        )
        return DevisOutput(
            mode="manuel",
            postes=postes,
            cout_revient_eur=cout_revient,
            pct_marge_appliquee=pct_marge,
            prix_vente_ht_eur=prix_vente_ht,
            prix_au_mille_eur=prix_au_mille,
        )

    def _compute_prix_au_mille_manuel(
        self,
        devis: DevisInput,
        prix_vente_ht: Decimal,
        intervalle_mm: Decimal,
    ) -> Decimal:
        """Formule Sprint 5 préservée (étiq par tirage total, floor une fois).

        nb_poses_developpement multiplié explicitement (Sprint 5 sémantique).
        """
        pas_mm = devis.format_etiquette_hauteur_mm + intervalle_mm
        etiq_par_pose_h = int(
            (Decimal(devis.ml_total) * Decimal(1000)) // pas_mm
        )
        nb_etiq_total = (
            devis.nb_poses_largeur
            * devis.nb_poses_developpement
            * etiq_par_pose_h
        )
        if nb_etiq_total <= 0:
            raise CostEngineError(
                f"nb_etiq_total = {nb_etiq_total} : tirage trop court pour la "
                f"hauteur étiquette {devis.format_etiquette_hauteur_mm} mm + "
                f"intervalle {intervalle_mm} mm"
            )
        return (prix_vente_ht * Decimal(1000) / Decimal(nb_etiq_total)).quantize(
            Decimal("0.01")
        )

    # -----------------------------------------------------------------------
    # Mode 'matching' (Sprint 7) — top 3 cylindres compatibles
    # -----------------------------------------------------------------------

    def _compute_matching(self, devis: DevisInput) -> DevisOutputMatching:
        machine = self.db.get(Machine, devis.machine_id)
        if machine is None:
            raise CostEngineError(f"Machine id={devis.machine_id} introuvable")

        # Largeur plaque = format_l × nb_poses_largeur (Règle 5 brief V2)
        largeur_plaque = Decimal(devis.format_etiquette_largeur_mm) * Decimal(
            devis.nb_poses_largeur
        )
        candidats = find_cylindre_candidats(
            format_h_mm=devis.format_etiquette_hauteur_mm,
            largeur_plaque_mm=largeur_plaque,
            machine=machine,
        )

        # Postes calculés UNE seule fois — ils ne dépendent pas du choix de
        # cylindre dans le moteur actuel (matière P1 / encres P2 / etc.
        # utilisent laize_utile et ml_total, indépendants de l'intervalle).
        postes: list[PosteResult] = [
            calc.calculer(devis) for calc in self._calculateurs
        ]
        cout_revient = sum(
            (p.montant_eur for p in postes), Decimal(0)
        ).quantize(Decimal("0.01"))
        pct_marge = self._resolve_pct_marge(devis)
        prix_vente_ht = (cout_revient * (Decimal(1) + pct_marge)).quantize(
            Decimal("0.01")
        )

        # Pour chaque candidat : prix_au_mille calculé avec la MÊME formule
        # que le mode manuel (Phase 2 fix précision matching 01/05/2026) :
        #   etiq_par_pose_h = floor((ml × 1000) / pas_mm)  ← UN seul floor sur le total
        #   nb_etiq_total   = nb_poses_l × nb_poses_d × etiq_par_pose_h
        #
        # Avant Phase 2 : le matching utilisait c.nb_etiq_par_metre (= floor(1000/pas))
        # × ml, qui jetait les fractions par mètre puis multipliait → perte de
        # précision ~7-8% sur les cas où pas_mm n'est pas multiple entier de 1000.
        # Symptôme : ratio prix_au_mille_matching/manuel = 1,078 sur cas Eric
        # 60×100 mm 2×2 poses, alors que mathématiquement il devrait être ~1,01
        # (le pas cylindre matching est très proche du pas manuel idéal).
        #
        # Le champ c.nb_etiq_par_metre reste exposé dans CandidatCylindreOutput
        # pour l'UI/PDF (indicateur visuel "9 étiq/m linéaire") mais n'est plus
        # utilisé pour le calcul prix.
        candidats_output: list[CandidatCylindreOutput] = []
        for c in candidats:
            etiq_par_pose_h = int(
                (Decimal(devis.ml_total) * Decimal(1000)) // c.pas_mm
            )
            nb_etiq_total = (
                devis.nb_poses_largeur
                * devis.nb_poses_developpement
                * etiq_par_pose_h
            )
            if nb_etiq_total <= 0:
                raise CostEngineError(
                    f"nb_etiq_total = {nb_etiq_total} pour cylindre Z={c.z}"
                )
            prix_au_mille = (
                prix_vente_ht * Decimal(1000) / Decimal(nb_etiq_total)
            ).quantize(Decimal("0.01"))
            candidats_output.append(
                CandidatCylindreOutput(
                    z=c.z,
                    nb_etiq_par_tour=c.nb_etiq_par_tour,
                    circonference_mm=c.circonference_mm,
                    pas_mm=c.pas_mm,
                    intervalle_mm=c.intervalle_mm,
                    nb_etiq_par_metre=c.nb_etiq_par_metre,
                    postes=postes,
                    cout_revient_eur=cout_revient,
                    pct_marge_appliquee=pct_marge,
                    prix_vente_ht_eur=prix_vente_ht,
                    prix_au_mille_eur=prix_au_mille,
                )
            )

        logger.info(
            "Devis MATCHING calculé: %d candidat(s), cout_revient=%s €, prix_HT=%s €, intervalle min=%s mm (Z=%d)",
            len(candidats_output),
            cout_revient,
            prix_vente_ht,
            candidats_output[0].intervalle_mm,
            candidats_output[0].z,
        )
        return DevisOutputMatching(candidats=candidats_output)

    def _resolve_pct_marge(self, devis: DevisInput) -> Decimal:
        if devis.pct_marge_override is not None:
            return devis.pct_marge_override
        entreprise = self.db.scalar(select(Entreprise).limit(1))
        if entreprise is None:
            raise CostEngineError(
                "Aucune entreprise configurée en base — pct_marge_defaut introuvable"
            )
        if entreprise.pct_marge_defaut is None:
            return PCT_MARGE_FALLBACK
        return Decimal(str(entreprise.pct_marge_defaut))
