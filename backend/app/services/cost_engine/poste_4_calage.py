"""Poste 4 — Mise en route / Calage (forfait machine).

Formule v1 (forfait simple) :
    cout = ConfigCouts.calage_forfait_eur  # 225 €/devis (démo ICE)

Mode "détaillé" prévu en évolution : cout = sum(operations × minutes ×
prix_horaire_machine) avec temps_operation_standard. À ne PAS faire en
3d (cf. project_devis_flexo_notes_futures). Le mode forfait actuel est
immune au double-compte avec P7 MO opérateur — l'évolution détaillée
devra y faire attention.

`details["mode"] = "forfait"` et `operations_count = 0` pour préparer
l'évolution future.

Phase 2 Lot 4a (2026-05-29) : le forfait passe de `TarifPoste.cle=
"calage_forfait"` (legacy, déprécié) à `ConfigCouts.calage_forfait_eur`
(Stratégique, scopée tenant).
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine._config_reader import get_config_couts_or_raise

logger = logging.getLogger(__name__)


class CalculateurPoste4Calage:
    POSTE_NUMERO = 4
    LIBELLE = "Mise en route / Calage"

    def __init__(self, db: Session, entreprise_id: int) -> None:
        """Sprint 12-C : `entreprise_id` requis pour scoper ConfigCouts."""
        self.db = db
        self.entreprise_id = entreprise_id

    def calculer(self, devis: DevisInput) -> PosteResult:
        config = get_config_couts_or_raise(self.db, self.entreprise_id)
        cout = Decimal(str(config.calage_forfait_eur)).quantize(Decimal("0.01"))

        logger.info("P4 Calage (forfait): %s €", cout)
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout,
            details={
                "mode": "forfait",
                "operations_count": 0,
                "forfait_eur": float(cout),
            },
        )
