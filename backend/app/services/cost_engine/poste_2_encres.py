"""Poste 2 — Encres.

Formule :
    surface_imprimee_m2 = (laize_utile_mm / 1000) × ml_total
    Pour chaque (type_encre, nb_couleurs) dans devis.nb_couleurs_par_type :
        tarif = tarif_encre.get_by_type_encre(type_encre)
        si tarif None → CostEngineError (pas de comportement silencieux)
        conso_kg = surface_imprimee_m2 × nb_couleurs × ratio_g_m2_couleur / 1000
        cout_partiel = conso_kg × prix_kg
    cout = somme cout_partiel

`ratio_g_m2_couleur` est la consommation moyenne d'encre par m² imprimé
et par couleur (typiquement 2.000 g/m²/couleur, défaut tarif_encre).
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.tarif_encre import get_by_type_encre
from app.schemas.devis import DevisInput
from app.schemas.poste_result import PosteResult
from app.services.cost_engine.errors import CostEngineError

logger = logging.getLogger(__name__)


class CalculateurPoste2Encres:
    POSTE_NUMERO = 2
    LIBELLE = "Encres"

    def __init__(self, db: Session) -> None:
        self.db = db

    def calculer(self, devis: DevisInput) -> PosteResult:
        surface_m2 = (
            Decimal(devis.laize_utile_mm) / Decimal(1000) * Decimal(devis.ml_total)
        )

        cout_total = Decimal(0)
        ventilation: dict[str, float | int | str] = {
            "surface_imprimee_m2": float(surface_m2),
        }
        for type_encre, nb_couleurs in devis.nb_couleurs_par_type.items():
            if nb_couleurs <= 0:
                continue
            tarif = get_by_type_encre(self.db, type_encre)
            if tarif is None:
                raise CostEngineError(
                    f"type_encre {type_encre!r} inconnu en base — vérifier seed tarif_encre"
                )
            ratio = Decimal(tarif.ratio_g_m2_couleur)
            prix_kg = Decimal(tarif.prix_kg_defaut)
            conso_kg = surface_m2 * Decimal(nb_couleurs) * ratio / Decimal(1000)
            cout_partiel = conso_kg * prix_kg
            cout_total += cout_partiel

            ventilation[f"{type_encre}_nb_couleurs"] = nb_couleurs
            ventilation[f"{type_encre}_prix_kg_eur"] = float(prix_kg)
            ventilation[f"{type_encre}_conso_kg"] = float(conso_kg)
            ventilation[f"{type_encre}_cout_partiel_eur"] = float(
                cout_partiel.quantize(Decimal("0.01"))
            )

        cout = cout_total.quantize(Decimal("0.01"))
        logger.info("P2 Encres: %s types → %s €", len(devis.nb_couleurs_par_type), cout)
        return PosteResult(
            poste_numero=self.POSTE_NUMERO,
            libelle=self.LIBELLE,
            montant_eur=cout,
            details=ventilation,
        )
