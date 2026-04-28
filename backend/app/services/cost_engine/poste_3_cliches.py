"""Poste 3 — Outillage / Clichés.

Formule :
    nb_couleurs_total = sum(devis.nb_couleurs_par_type.values())
    cout = nb_couleurs_total × tarif("cliche_prix_couleur")

Hypothèse v1 : pas de gestion réédition outil usé (réservé S4 — note
project_devis_flexo_notes_futures). Tous les clichés sont neufs ou
re-facturés pleins. Si réédition à -20 %, gérer en override manuel.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_poste import get_by_cle
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


class CalculateurPoste3Cliches:
    POSTE_NUMERO = 3
    LIBELLE = "Outillage / Clichés"

    def __init__(self, db: Session) -> None:
        self.db = db

    def calculer(self, devis: DevisInput) -> PosteResult:
        tarif = get_by_cle(self.db, "cliche_prix_couleur")
        if tarif is None:
            raise CostEngineError(
                "Tarif 'cliche_prix_couleur' introuvable — seed tarif_poste manquant"
            )
        prix_couleur = Decimal(tarif.valeur_defaut)
        nb_couleurs_total = sum(devis.nb_couleurs_par_type.values())
        cout = (Decimal(nb_couleurs_total) * prix_couleur).quantize(Decimal("0.01"))

        logger.info("P3 Clichés: %s couleurs × %s €/couleur = %s €",
                    nb_couleurs_total, prix_couleur, cout)
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout,
            details={
                "nb_couleurs_total": nb_couleurs_total,
                "prix_par_couleur_eur": float(prix_couleur),
            },
        )
