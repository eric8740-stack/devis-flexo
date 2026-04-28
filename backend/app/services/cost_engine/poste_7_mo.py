"""Poste 7 — Main d'œuvre opérateur.

Formule :
    heures_calage = machine.duree_calage_h
    heures_production = ml_total / machine.vitesse_moyenne_m_h
    heures_total = heures_calage + heures_production
    SI devis.heures_dossier_override est fourni → heures_total = override
    cout = heures_total × tarif("mo_prix_horaire")

NB métier : le temps de calage est rémunéré à la fois ici (P7 = MO
opérateur qui règle) ET en P4 (forfait MACHINE pendant calage). Ce
double-compte est INTENTIONNEL — deux ressources distinctes (machine
immobilisée + humain qui règle). Cohérent avec la pratique flexo.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_poste import get_by_cle
from app.models import Machine
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


class CalculateurPoste7MO:
    POSTE_NUMERO = 7
    LIBELLE = "Main d'œuvre opérateur"

    def __init__(self, db: Session) -> None:
        self.db = db

    def calculer(self, devis: DevisInput) -> PosteResult:
        tarif = get_by_cle(self.db, "mo_prix_horaire")
        if tarif is None:
            raise CostEngineError(
                "Tarif 'mo_prix_horaire' introuvable — seed manquant"
            )
        prix_h = Decimal(tarif.valeur_defaut)

        if devis.heures_dossier_override is not None:
            heures_total = devis.heures_dossier_override
            heures_calage = Decimal(0)
            heures_production = Decimal(0)
            source = "override"
        else:
            machine = self.db.get(Machine, devis.machine_id)
            if machine is None:
                raise CostEngineError(
                    f"Machine id={devis.machine_id} introuvable"
                )
            if not machine.vitesse_moyenne_m_h or machine.vitesse_moyenne_m_h <= 0:
                raise CostEngineError(
                    f"Machine id={devis.machine_id} ({machine.nom}) "
                    "n'a pas de vitesse_moyenne_m_h > 0, requise pour P7"
                )
            heures_calage = Decimal(machine.duree_calage_h or 0)
            heures_production = (
                Decimal(devis.ml_total) / Decimal(machine.vitesse_moyenne_m_h)
            )
            heures_total = heures_calage + heures_production
            source = "derived_machine"

        cout = (heures_total * prix_h).quantize(Decimal("0.01"))
        logger.info(
            "P7 MO: %s h (calage=%s + prod=%s, source=%s) × %s €/h = %s €",
            heures_total, heures_calage, heures_production, source, prix_h, cout,
        )
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout,
            details={
                "heures_calage": float(heures_calage),
                "heures_production": float(heures_production),
                "heures_total": float(heures_total),
                "heures_source": source,
                "prix_horaire_mo_eur": float(prix_h),
            },
        )
