from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PrestationType = Literal["finition", "decoupe", "dorure", "autre"]
StatutPartenaire = Literal["actif", "inactif"]


class PartenaireSTBase(BaseModel):
    raison_sociale: str = Field(min_length=1, max_length=150)
    siret: str | None = Field(default=None, max_length=14)
    contact_nom: str | None = Field(default=None, max_length=100)
    contact_email: str | None = Field(default=None, max_length=150)
    contact_tel: str | None = Field(default=None, max_length=30)
    prestation_type: PrestationType | None = None
    delai_jours_moyen: int | None = Field(default=None, ge=0)
    qualite_score: int | None = Field(default=None, ge=1, le=5)
    commentaire: str | None = None
    statut: StatutPartenaire = "actif"


class PartenaireSTRead(PartenaireSTBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class PartenaireSTCreate(PartenaireSTBase):
    pass


class PartenaireSTUpdate(BaseModel):
    raison_sociale: str | None = Field(default=None, min_length=1, max_length=150)
    siret: str | None = Field(default=None, max_length=14)
    contact_nom: str | None = Field(default=None, max_length=100)
    contact_email: str | None = Field(default=None, max_length=150)
    contact_tel: str | None = Field(default=None, max_length=30)
    prestation_type: PrestationType | None = None
    delai_jours_moyen: int | None = Field(default=None, ge=0)
    qualite_score: int | None = Field(default=None, ge=1, le=5)
    commentaire: str | None = None
    statut: StatutPartenaire | None = None
