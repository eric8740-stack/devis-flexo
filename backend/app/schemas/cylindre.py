"""Schémas Pydantic — CRUD /api/cylindres (Brief #29).

Côté API on accepte/expose `nb_dents` (nomenclature métier flexo : un
imprimeur désigne un cylindre par son nombre de dents, pas par son
développé). La conversion vers `developpe_mm` est faite côté CRUD via
DENTS_TO_MM_FACTOR = 3.175 mm/dent.

Le modèle CylindreMagnetique stocke `developpe_mm` directement (cf
fix Cas B 2026-05-16). La sortie API expose les deux pour faciliter
l'UI et la cohérence métier.
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


# Bornes raisonnables flexo (cf brief #29) : 20 à 300 dents.
NbDents = Annotated[int, Field(ge=20, le=300)]


class CylindreCreate(BaseModel):
    """Body POST /api/cylindres."""

    model_config = ConfigDict(extra="forbid")

    nb_dents: NbDents
    actif: bool = True
    notes: str | None = Field(None, max_length=1000)


class CylindreUpdate(BaseModel):
    """Body PATCH /api/cylindres/{id} — champs partiels."""

    model_config = ConfigDict(extra="forbid")

    nb_dents: NbDents | None = None
    actif: bool | None = None
    notes: str | None = Field(None, max_length=1000)


class CylindreRead(BaseModel):
    """Détail GET /api/cylindres/{id} + retour POST/PATCH."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nb_dents: int
    developpe_mm: Decimal
    actif: bool
    notes: str | None = None
    date_creation: datetime
