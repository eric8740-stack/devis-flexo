"""Poste 1 — Matière.

Formule :
    laize_machine_mm = laize_utile_mm + ConfigCouts.marge_confort_roulage_mm
    surface_support_m2 = (laize_machine_mm / 1000) × ml_total
    poids_kg = surface_support_m2 × grammage_g_m2 / 1000
    cout = poids_kg × prix_kg

prix_kg : dérivé de complexe.prix_m2_eur si défini, fallback tarif global.
    Si complexe.prix_m2_eur ET grammage défini :
        prix_kg = prix_m2_eur × 1000 / grammage_g_m2
        details["prix_kg_source"] = "complexe_derived"
    Sinon :
        prix_kg = tarif("matiere_prix_kg_defaut")    ← reste sur TarifPoste
        details["prix_kg_source"] = "fallback_tarif_global"

Justification dérivation : le métier flexo raisonne au kg (rouleaux pesés),
mais les fournisseurs facturent au m². On expose le passage par prix_kg
pour rester défendable en démo.

Phase 2 Lot 4a (2026-05-29) : la marge de confort passe de `TarifPoste.cle=
"marge_confort_roulage_mm"` (legacy, déprécié) à `ConfigCouts.marge_confort_
roulage_mm` (Stratégique, scopée tenant). Le fallback prix_kg
`matiere_prix_kg_defaut` reste sur `TarifPoste` (chemin rare ; depuis Lot 1
complexe enrichi, tous les complexes démo ont prix_m2_eur + grammage — le
fallback n'est plus exécuté en pratique, migration séparée si nécessaire).
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_poste import get_by_cle
from app.models import Complexe
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine._config_reader import get_config_couts_or_raise
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


class CalculateurPoste1Matiere:
    POSTE_NUMERO = 1
    LIBELLE = "Matière"

    def __init__(self, db: Session, entreprise_id: int) -> None:
        """Sprint 12-C : `entreprise_id` requis pour scoper ConfigCouts +
        le fallback TarifPoste matiere_prix_kg_defaut."""
        self.db = db
        self.entreprise_id = entreprise_id

    def calculer(self, devis: DevisInput) -> PosteResult:
        complexe = self.db.get(Complexe, devis.complexe_id)
        if complexe is None:
            raise CostEngineError(
                f"Complexe id={devis.complexe_id} introuvable"
            )

        config = get_config_couts_or_raise(self.db, self.entreprise_id)
        marge_mm = int(config.marge_confort_roulage_mm)

        # Dérivation prix_kg depuis le complexe, fallback tarif global
        prix_kg, prix_kg_source = self._resolve_prix_kg(complexe)

        # Grammage requis pour passer du m² au kg
        if complexe.grammage_g_m2 is None:
            raise CostEngineError(
                f"Complexe id={devis.complexe_id} ({complexe.reference}) "
                "n'a pas de grammage_g_m2 défini, requis pour P1"
            )

        laize_machine_mm = devis.laize_utile_mm + marge_mm
        surface_support_m2 = (
            Decimal(laize_machine_mm) / Decimal(1000) * Decimal(devis.ml_total)
        )
        poids_kg = surface_support_m2 * Decimal(complexe.grammage_g_m2) / Decimal(1000)
        cout = (poids_kg * prix_kg).quantize(Decimal("0.01"))

        logger.info(
            "P1 Matière: %s m² × %s g/m² → %s kg × %s €/kg = %s € (source=%s)",
            surface_support_m2, complexe.grammage_g_m2, poids_kg, prix_kg,
            cout, prix_kg_source,
        )
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout,
            details={
                "complexe_id": devis.complexe_id,
                "complexe_reference": complexe.reference,
                "grammage_g_m2": int(complexe.grammage_g_m2),
                "marge_confort_roulage_mm": marge_mm,
                "laize_utile_mm": devis.laize_utile_mm,
                "laize_machine_mm": laize_machine_mm,
                "surface_support_m2": float(surface_support_m2),
                "poids_kg": float(poids_kg),
                "prix_kg_eur": float(prix_kg),
                "prix_kg_source": prix_kg_source,
            },
        )

    def _resolve_prix_kg(self, complexe: Complexe) -> tuple[Decimal, str]:
        """Dérive prix_kg depuis prix_m2 du complexe, fallback tarif global."""
        if complexe.prix_m2_eur is not None and complexe.grammage_g_m2:
            prix_kg = (
                Decimal(complexe.prix_m2_eur)
                * Decimal(1000)
                / Decimal(complexe.grammage_g_m2)
            )
            return prix_kg, "complexe_derived"

        tarif_fallback = get_by_cle(
            self.db, "matiere_prix_kg_defaut", self.entreprise_id
        )
        if tarif_fallback is None:
            raise CostEngineError(
                "Tarif 'matiere_prix_kg_defaut' introuvable — fallback impossible"
            )
        return Decimal(tarif_fallback.valeur_defaut), "fallback_tarif_global"
