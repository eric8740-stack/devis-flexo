from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FrequenceEstimee = Literal["ponctuelle", "mensuelle", "trimestrielle", "annuelle"]
StatutCatalogue = Literal["actif", "archive"]


class CatalogueBase(BaseModel):
    code_produit: str = Field(min_length=1, max_length=50)
    designation: str = Field(min_length=1, max_length=200)
    client_id: int
    machine_id: int | None = None
    matiere: str | None = Field(default=None, max_length=100)
    format_mm: str | None = Field(default=None, max_length=50)
    nb_couleurs: int | None = Field(default=None, ge=0, le=12)
    prix_unitaire_eur: float | None = Field(default=None, ge=0)
    frequence_estimee: FrequenceEstimee | None = None
    commentaire: str | None = None
    statut: StatutCatalogue = "actif"


class CatalogueRead(CatalogueBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class CatalogueCreate(CatalogueBase):
    pass


class CatalogueUpdate(BaseModel):
    code_produit: str | None = Field(default=None, min_length=1, max_length=50)
    designation: str | None = Field(default=None, min_length=1, max_length=200)
    client_id: int | None = None
    machine_id: int | None = None
    matiere: str | None = Field(default=None, max_length=100)
    format_mm: str | None = Field(default=None, max_length=50)
    nb_couleurs: int | None = Field(default=None, ge=0, le=12)
    prix_unitaire_eur: float | None = Field(default=None, ge=0)
    frequence_estimee: FrequenceEstimee | None = None
    commentaire: str | None = None
    statut: StatutCatalogue | None = None
