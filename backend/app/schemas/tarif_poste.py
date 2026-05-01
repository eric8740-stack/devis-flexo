from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TarifPosteBase(BaseModel):
    cle: str = Field(min_length=1, max_length=50)
    poste_numero: int = Field(ge=1, le=7)
    libelle: str = Field(min_length=1, max_length=150)
    valeur_defaut: Decimal
    valeur_min: Decimal | None = None
    valeur_max: Decimal | None = None
    unite: str = Field(min_length=1, max_length=30)
    actif: bool = True
    description: str | None = None
    ordre_affichage: int = Field(default=0, ge=0)


class TarifPosteRead(TarifPosteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class TarifPosteCreate(TarifPosteBase):
    """Body POST."""


class TarifPosteUpdate(BaseModel):
    """Body PUT : tous les champs optionnels (partial update via exclude_unset)."""

    cle: str | None = Field(default=None, min_length=1, max_length=50)
    poste_numero: int | None = Field(default=None, ge=1, le=7)
    libelle: str | None = Field(default=None, min_length=1, max_length=150)
    valeur_defaut: Decimal | None = None
    valeur_min: Decimal | None = None
    valeur_max: Decimal | None = None
    unite: str | None = Field(default=None, min_length=1, max_length=30)
    actif: bool | None = None
    description: str | None = None
    ordre_affichage: int | None = Field(default=None, ge=0)
