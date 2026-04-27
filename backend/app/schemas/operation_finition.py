from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UniteFacturation = Literal["m2", "ml", "unite", "millier"]
StatutOperation = Literal["actif", "inactif"]


class OperationFinitionBase(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    unite_facturation: UniteFacturation
    cout_unitaire_eur: float | None = Field(default=None, ge=0)
    temps_minutes_unite: float | None = Field(default=None, ge=0)
    statut: StatutOperation = "actif"
    commentaire: str | None = None


class OperationFinitionRead(OperationFinitionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class OperationFinitionCreate(OperationFinitionBase):
    pass


class OperationFinitionUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    unite_facturation: UniteFacturation | None = None
    cout_unitaire_eur: float | None = Field(default=None, ge=0)
    temps_minutes_unite: float | None = Field(default=None, ge=0)
    statut: StatutOperation | None = None
    commentaire: str | None = None
