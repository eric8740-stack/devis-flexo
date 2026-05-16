"""Schémas Pydantic — Paramètres > Options de fabrication (CRUD tenant).

Page UI `/parametres/options-fabrication` : permet au tenant d'activer/
désactiver les 21 options du catalogue master Sprint 13, d'éditer les coefs
vitesse/gâche et de renseigner la tarification (forfait_eur, prix_au_m2_eur,
prix_au_mille_eur, cout_consommable_eur).

Pas de création custom dans ce MVP (les 21 codes du catalogue master sont la
seule source d'options activables). Pas de hard delete (toggle `actif`).
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OptionFabricationTenantOut(BaseModel):
    """Une option de fabrication scopée tenant, telle qu'elle apparaît dans
    la page Paramètres > Options de fabrication.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    code: str
    libelle: str
    categorie: str | None = None
    description: str | None = None

    coef_vitesse_impact: Decimal
    coef_gache_impact: Decimal
    ajoute_temps_calage_min: int

    forfait_eur: Decimal | None = None
    prix_au_m2_eur: Decimal | None = None
    prix_au_mille_eur: Decimal | None = None
    cout_consommable_eur: Decimal | None = None

    actif: bool

    # Snapshot des valeurs catalogue master au moment de l'activation
    # (None pour les options globales / pré-existantes). Le frontend
    # l'utilise pour afficher "(recommandé : X.XX)" dans le dialog
    # d'édition.
    valeur_recommandee_origine: dict | None = None


class OptionFabricationUpdate(BaseModel):
    """Body de PATCH /api/parametres/options-fabrication/{id}.

    Tous champs optionnels — seuls les champs présents sont modifiés.
    `code`, `libelle`, `categorie`, `description` sont volontairement
    immuables (figés au moment de l'activation depuis le master) pour
    éviter de désynchroniser l'UI tenant du catalogue partagé.
    """

    model_config = ConfigDict(extra="forbid")

    coef_vitesse_impact: Decimal | None = Field(
        default=None, ge=Decimal("0.1"), le=Decimal("2.0")
    )
    coef_gache_impact: Decimal | None = Field(
        default=None, ge=Decimal("0.5"), le=Decimal("3.0")
    )
    forfait_eur: Decimal | None = Field(default=None, ge=Decimal("0"))
    prix_au_m2_eur: Decimal | None = Field(default=None, ge=Decimal("0"))
    prix_au_mille_eur: Decimal | None = Field(default=None, ge=Decimal("0"))
    cout_consommable_eur: Decimal | None = Field(default=None, ge=Decimal("0"))
    actif: bool | None = None
