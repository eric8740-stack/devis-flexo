"""Poste 6 — Finitions (internes + sous-traitance).

Formule :
    surface_imprimee_m2 = (laize_utile_mm / 1000) × ml_total
    cout_finitions_base = surface_imprimee_m2 × tarif("finitions_prix_m2")
    cout_st = sum(forfait.montant_eur for forfait in devis.forfaits_st)
    cout = cout_finitions_base + cout_st

Note : surface UTILE (pas surface support — la marge_confort est consommée
par P1 mais ne reçoit pas de finition).
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_poste import get_by_cle
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine._config_reader import get_config_couts_or_raise
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


class CalculateurPoste6Finitions:
    POSTE_NUMERO = 6
    LIBELLE = "Finitions"

    def __init__(self, db: Session, entreprise_id: int) -> None:
        """Sprint 12-C : `entreprise_id` requis pour scoper tarif_poste."""
        self.db = db
        self.entreprise_id = entreprise_id

    def calculer(self, devis: DevisInput) -> PosteResult:
        # Phase 2 / Lot 4a — `finitions_prix_m2_eur` lue depuis `ConfigCouts`
        # scopée tenant via reader DRY (anciennement clé `finitions_prix_m2`
        # rangée comme row sur `tarif_poste`, dépréciée mais conservée).
        config = get_config_couts_or_raise(self.db, self.entreprise_id)
        prix_m2 = Decimal(config.finitions_prix_m2_eur)
        surface_m2 = Decimal(devis.laize_utile_mm) / Decimal(1000) * Decimal(devis.ml_total)
        cout_base = (surface_m2 * prix_m2).quantize(Decimal("0.01"))
        cout_st = sum(
            (forfait.montant_eur for forfait in devis.forfaits_st), Decimal(0)
        )
        cout = (cout_base + cout_st).quantize(Decimal("0.01"))

        logger.info("P6 Finitions: base=%s € + ST=%s € = %s €",
                    cout_base, cout_st, cout)
        details: dict[str, float | int | str] = {
            "surface_imprimee_m2": float(surface_m2),
            "prix_finitions_m2": float(prix_m2),
            "cout_finitions_base_eur": float(cout_base),
            "cout_st_total_eur": float(cout_st),
            "nb_forfaits_st": len(devis.forfaits_st),
        }
        for forfait in devis.forfaits_st:
            details[f"forfait_st_partenaire_{forfait.partenaire_st_id}"] = float(
                forfait.montant_eur
            )
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout,
            details=details,
        )
