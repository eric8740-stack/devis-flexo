"""Orchestrateur du moteur de coût v2.

Instancie les 7 calculateurs, les invoque dans l'ordre, agrège les
PosteResult dans DevisOutput.postes, calcule cout_revient + prix_vente_ht.

Le pct_marge appliqué vient de devis.pct_marge_override si fourni, sinon
de entreprise.pct_marge_defaut. Si entreprise n'a pas de marge configurée,
fallback à 0.18 (preset Compétitif persona PRD).
"""
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entreprise
from app.schemas.devis import DevisInput, DevisOutput
from app.services.cost_engine.errors import CostEngineError
from app.services.cost_engine.poste_1_matiere import CalculateurPoste1Matiere
from app.services.cost_engine.poste_2_encres import CalculateurPoste2Encres
from app.services.cost_engine.poste_3_cliches import CalculateurPoste3Cliches
from app.services.cost_engine.poste_4_calage import CalculateurPoste4Calage
from app.services.cost_engine.poste_5_roulage import CalculateurPoste5Roulage
from app.services.cost_engine.poste_6_finitions import CalculateurPoste6Finitions
from app.services.cost_engine.poste_7_mo import CalculateurPoste7MO

logger = logging.getLogger(__name__)

PCT_MARGE_FALLBACK = Decimal("0.18")  # preset Compétitif persona PRD


class MoteurDevis:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._calculateurs = [
            CalculateurPoste1Matiere(db),
            CalculateurPoste2Encres(db),
            CalculateurPoste3Cliches(db),
            CalculateurPoste4Calage(db),
            CalculateurPoste5Roulage(db),
            CalculateurPoste6Finitions(db),
            CalculateurPoste7MO(db),
        ]

    def calculer(self, devis: DevisInput) -> DevisOutput:
        postes = [calc.calculer(devis) for calc in self._calculateurs]

        cout_revient = sum(
            (p.montant_eur for p in postes), Decimal(0)
        ).quantize(Decimal("0.01"))

        pct_marge = self._resolve_pct_marge(devis)
        prix_vente_ht = (cout_revient * (Decimal(1) + pct_marge)).quantize(
            Decimal("0.01")
        )

        logger.info(
            "Devis calculé: cout_revient=%s €, marge=%s, prix_vente_HT=%s €",
            cout_revient, pct_marge, prix_vente_ht,
        )
        return DevisOutput(
            postes=postes,
            cout_revient_eur=cout_revient,
            pct_marge_appliquee=pct_marge,
            prix_vente_ht_eur=prix_vente_ht,
        )

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
