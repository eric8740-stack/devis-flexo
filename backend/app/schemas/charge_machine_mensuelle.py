from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ChargeMachineMensuelleBase(BaseModel):
    mois: int = Field(ge=1, le=12)
    annee: int = Field(ge=2024)
    montant_total: Decimal = Field(ge=0)
    heures_disponibles: Decimal = Field(gt=0)
    source: str | None = Field(default=None, max_length=100)


class ChargeMachineMensuelleRead(ChargeMachineMensuelleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cout_horaire_calcule: Decimal
    date_creation: datetime
    date_maj: datetime


class ChargeMachineMensuelleCreate(ChargeMachineMensuelleBase):
    """Body POST. cout_horaire_calcule absent : recalculé par hook applicatif."""


class ChargeMachineMensuelleUpdate(BaseModel):
    mois: int | None = Field(default=None, ge=1, le=12)
    annee: int | None = Field(default=None, ge=2024)
    montant_total: Decimal | None = Field(default=None, ge=0)
    heures_disponibles: Decimal | None = Field(default=None, gt=0)
    source: str | None = Field(default=None, max_length=100)
