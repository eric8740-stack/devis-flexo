from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CategorieCharge = Literal[
    "loyer", "salaires", "energie", "assurance", "fournitures", "autre"
]


class ChargeMensuelleBase(BaseModel):
    libelle: str = Field(min_length=1, max_length=150)
    categorie: CategorieCharge
    montant_eur: float = Field(ge=0)
    date_debut: date
    date_fin: date | None = None
    commentaire: str | None = None


class ChargeMensuelleRead(ChargeMensuelleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class ChargeMensuelleCreate(ChargeMensuelleBase):
    pass


class ChargeMensuelleUpdate(BaseModel):
    libelle: str | None = Field(default=None, min_length=1, max_length=150)
    categorie: CategorieCharge | None = None
    montant_eur: float | None = Field(default=None, ge=0)
    date_debut: date | None = None
    date_fin: date | None = None
    commentaire: str | None = None
