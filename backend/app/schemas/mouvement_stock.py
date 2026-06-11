"""Schémas Pydantic — CRUD mouvements de stock (Module Stock S2).

`ml` est TOUJOURS positif : le `type` porte le sens (entree +, sortie −,
inventaire = nouvelle valeur cible). Le POST renvoie le couple
`{mouvement, bobine}` pour que le front affiche immédiatement le `ml_restant`
recalculé.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bobine import BobineOut


# Types de mouvement (le cycle pourra s'enrichir en S3).
TYPES_MOUVEMENT = ("entree", "sortie", "inventaire")


class MouvementCreate(BaseModel):
    """Body POST mouvement.

    `ml` > 0 dans tous les cas. Pour `inventaire`, `ml` est la NOUVELLE valeur
    de `ml_restant` (correction), pas un delta.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(pattern="^(entree|sortie|inventaire)$")
    ml: int = Field(gt=0)
    motif: str | None = Field(None, max_length=200)
    reference: str | None = Field(None, max_length=100)


class MouvementOut(BaseModel):
    """Ligne du journal d'audit."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bobine_id: int
    devis_id: int | None = None
    type: str
    ml: int
    ml_avant: int
    ml_apres: int
    motif: str | None = None
    reference: str | None = None
    date_creation: datetime


class MouvementResult(BaseModel):
    """Retour POST mouvement : le mouvement créé + la bobine ré-évaluée."""

    model_config = ConfigDict(from_attributes=True)

    mouvement: MouvementOut
    bobine: BobineOut
