"""Poste 4 — Mise en route / Calage (forfait machine).

Formule v1 (forfait simple) :
    cout = tarif("calage_forfait")  # 225 €/devis par défaut

Mode "détaillé" prévu en évolution : cout = sum(operations × minutes ×
prix_horaire_machine) avec temps_operation_standard. À ne PAS faire en
3d (cf. project_devis_flexo_notes_futures). Le mode forfait actuel est
immune au double-compte avec P7 MO opérateur — l'évolution détaillée
devra y faire attention.

`details["mode"] = "forfait"` et `operations_count = 0` pour préparer
l'évolution future.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_poste import get_by_cle
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


class CalculateurPoste4Calage:
    POSTE_NUMERO = 4
    LIBELLE = "Mise en route / Calage"

    def __init__(self, db: Session, entreprise_id: int) -> None:
        """Sprint 12-C : `entreprise_id` requis pour scoper tarif_poste."""
        self.db = db
        self.entreprise_id = entreprise_id

    def calculer(self, devis: DevisInput) -> PosteResult:
        tarif = get_by_cle(self.db, "calage_forfait", self.entreprise_id)
        if tarif is None:
            raise CostEngineError(
                "Tarif 'calage_forfait' introuvable — seed tarif_poste manquant"
            )
        cout = Decimal(tarif.valeur_defaut).quantize(Decimal("0.01"))

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
