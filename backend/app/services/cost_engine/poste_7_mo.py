"""Poste 7 — Main d'œuvre opérateur.

Formule :
    heures_calage = machine.duree_calage_h
    heures_production = ml_total / machine.vitesse_moyenne_m_h
    heures_total = heures_calage + heures_production
    SI devis.heures_dossier_override est fourni → heures_total = override
    cout = heures_total × ConfigCouts.cout_operateur_eur_h

NB métier : le temps de calage est rémunéré à la fois ici (P7 = MO
opérateur qui règle) ET en P4 (forfait MACHINE pendant calage). Ce
double-compte est INTENTIONNEL — deux ressources distinctes (machine
immobilisée + humain qui règle). Cohérent avec la pratique flexo.

Phase 2 Lot 3 (2026-05-28) : le prix horaire MO passe de `TarifPoste.
cle="mo_prix_horaire"` (legacy, déprécié) à `ConfigCouts.
cout_operateur_eur_h` (Stratégique, scopée tenant).
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Machine
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine._config_reader import get_config_couts_or_raise
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


class CalculateurPoste7MO:
    POSTE_NUMERO = 7
    LIBELLE = "Main d'œuvre opérateur"

    def __init__(self, db: Session, entreprise_id: int) -> None:
        """Sprint 12-C : `entreprise_id` requis pour scoper ConfigCouts."""
        self.db = db
        self.entreprise_id = entreprise_id

    def calculer(self, devis: DevisInput) -> PosteResult:
        config = get_config_couts_or_raise(self.db, self.entreprise_id)
        prix_h = Decimal(str(config.cout_operateur_eur_h))

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
