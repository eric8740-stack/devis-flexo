"""Schémas Pydantic — lien devis↔stock (Module Stock S3).

Lecture seule côté devis (matière + laize + `bobinage.ml_total` du calcul F).
La consommation réutilise `MouvementStock` (type `sortie`, `devis_id` renseigné)
— aucune modif du modèle Devis, aucune migration.
"""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bobine import BobineOut
from app.schemas.mouvement_stock import MouvementOut


class PropositionLigne(BaseModel):
    """Une bobine proposée (FIFO) pour couvrir le besoin du devis."""

    model_config = ConfigDict(from_attributes=True)

    bobine_id: int
    emplacement: str
    laize_mm: float
    ml_restant: int
    ml_propose: int


class PropositionOut(BaseModel):
    """Proposition de consommation FIFO (ajustable côté front avant POST).

    Si `deja_consomme` : le front affiche « consommé + Annuler » au lieu de la
    proposition (le back refuse de toute façon une 2ᵉ consommation, cf. POST).
    """

    ml_requis: float
    lignes: list[PropositionLigne] = Field(default_factory=list)
    stock_suffisant: bool
    manque_ml: float
    # Amendement gap #4 — état de consommation du devis (déduit des mouvements).
    deja_consomme: bool = False
    consomme_ml: float = 0.0
    mouvements: list[MouvementOut] = Field(default_factory=list)


class ConsommerLigne(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bobine_id: int = Field(gt=0)
    ml: int = Field(gt=0)


class ConsommerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lignes: list[ConsommerLigne] = Field(min_length=1)


class ConsommationResult(BaseModel):
    """Retour POST consommer / annuler : mouvements créés + bobines ré-évaluées."""

    model_config = ConfigDict(from_attributes=True)

    mouvements: list[MouvementOut] = Field(default_factory=list)
    bobines: list[BobineOut] = Field(default_factory=list)
