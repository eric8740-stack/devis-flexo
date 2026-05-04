"""Poste 5 — Roulage (presse en production).

Formule :
    temps_production_h = ml_total / machine.vitesse_moyenne_m_h
    cout = temps_production_h × tarif("roulage_prix_horaire")

vitesse_moyenne_m_h est la vitesse réaliste de roulage (vs vitesse_max_m_min
qui reste un argument catalogue). Si NULL ou ≤ 0 sur la machine, on lève
une erreur explicite plutôt que d'utiliser un fallback silencieux.

NB : ce poste couvre le coût horaire MACHINE pendant le roulage. Le coût
horaire MO opérateur est en P7 (ressources distinctes : machine + humain).
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


class CalculateurPoste5Roulage:
    POSTE_NUMERO = 5
    LIBELLE = "Roulage"

    def __init__(self, db: Session, entreprise_id: int) -> None:
        """Sprint 12-C : `entreprise_id` requis pour scoper tarif_poste."""
        self.db = db
        self.entreprise_id = entreprise_id

    def calculer(self, devis: DevisInput) -> PosteResult:
        machine = self.db.get(Machine, devis.machine_id)
        if machine is None:
            raise CostEngineError(f"Machine id={devis.machine_id} introuvable")
        if not machine.vitesse_moyenne_m_h or machine.vitesse_moyenne_m_h <= 0:
            raise CostEngineError(
                f"Machine id={devis.machine_id} ({machine.nom}) "
                "n'a pas de vitesse_moyenne_m_h > 0, requise pour P5"
            )

        tarif = get_by_cle(self.db, "roulage_prix_horaire", self.entreprise_id)
        if tarif is None:
            raise CostEngineError(
                "Tarif 'roulage_prix_horaire' introuvable — seed manquant"
            )
        prix_h = Decimal(tarif.valeur_defaut)

        temps_h = Decimal(devis.ml_total) / Decimal(machine.vitesse_moyenne_m_h)
        cout = (temps_h * prix_h).quantize(Decimal("0.01"))

        logger.info(
            "P5 Roulage: %s ml ÷ %s m/h = %s h × %s €/h = %s €",
            devis.ml_total, machine.vitesse_moyenne_m_h, temps_h, prix_h, cout,
        )
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout,
            details={
                "machine_id": devis.machine_id,
                "machine_nom": machine.nom,
                "vitesse_moyenne_m_h": int(machine.vitesse_moyenne_m_h),
                "ml_total": devis.ml_total,
                "temps_production_h": float(temps_h),
                "prix_horaire_eur": float(prix_h),
            },
        )
