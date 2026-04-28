from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TempsOperationStandardBase(BaseModel):
    libelle_operation: str = Field(min_length=1, max_length=150)
    minutes_standard: Decimal = Decimal("5.00")
    categorie: str | None = Field(default=None, max_length=50)
    ordre_affichage: int = Field(ge=0)
    actif: bool = True


class TempsOperationStandardRead(TempsOperationStandardBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class TempsOperationStandardCreate(TempsOperationStandardBase):
    """Body POST."""


class TempsOperationStandardUpdate(BaseModel):
    libelle_operation: str | None = Field(default=None, min_length=1, max_length=150)
    minutes_standard: Decimal | None = None
    categorie: str | None = Field(default=None, max_length=50)
    ordre_affichage: int | None = Field(default=None, ge=0)
    actif: bool | None = None
