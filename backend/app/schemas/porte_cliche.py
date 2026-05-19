"""Schémas Pydantic — CRUD /api/porte-cliches (Brief #29).

Le porte-cliché (sleeve) est un support physique réutilisable distinct
du cylindre magnétique. Référence unique par entreprise.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PorteClicheCreate(BaseModel):
    """Body POST /api/porte-cliches."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(min_length=1, max_length=50)
    marque: str | None = Field(None, max_length=80)
    modele: str | None = Field(None, max_length=80)
    laize_utile_mm: Decimal = Field(gt=0, le=2000)
    diametre_interieur_mm: Decimal | None = Field(None, gt=0, le=1000)
    matiere: str | None = Field(None, max_length=40)
    notes: str | None = Field(None, max_length=1000)
    actif: bool = True


class PorteClicheUpdate(BaseModel):
    """Body PATCH /api/porte-cliches/{id} — champs partiels."""

    model_config = ConfigDict(extra="forbid")

    reference: str | None = Field(None, min_length=1, max_length=50)
    marque: str | None = Field(None, max_length=80)
    modele: str | None = Field(None, max_length=80)
    laize_utile_mm: Decimal | None = Field(None, gt=0, le=2000)
    diametre_interieur_mm: Decimal | None = Field(None, gt=0, le=1000)
    matiere: str | None = Field(None, max_length=40)
    notes: str | None = Field(None, max_length=1000)
    actif: bool | None = None


class PorteClicheRead(BaseModel):
    """Détail GET /api/porte-cliches/{id} + retour POST/PATCH."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    marque: str | None
    modele: str | None
    laize_utile_mm: Decimal
    diametre_interieur_mm: Decimal | None
    matiere: str | None
    notes: str | None
    actif: bool
    created_at: datetime
    updated_at: datetime
