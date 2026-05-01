from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OutilDecoupeBase(BaseModel):
    """Champs partagés entre Create / Read pour le CRUD Sprint 9 v2 Lot 9d."""

    libelle: str = Field(min_length=1, max_length=100)
    format_l_mm: int = Field(gt=0)
    format_h_mm: int = Field(gt=0)
    nb_poses_l: int = Field(ge=1)
    nb_poses_h: int = Field(ge=1)
    forme_speciale: bool = False
    actif: bool = True


class OutilDecoupeRead(OutilDecoupeBase):
    """Sortie API GET — utilisée par le select frontend Lot 5d + UI catalogue
    Sprint 9 v2."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date_creation: datetime


class OutilDecoupeCreate(OutilDecoupeBase):
    """Body POST Sprint 9 v2 Lot 9d."""


class OutilDecoupeUpdate(BaseModel):
    """Body PUT : tous les champs optionnels (partial update via exclude_unset)."""

    libelle: str | None = Field(default=None, min_length=1, max_length=100)
    format_l_mm: int | None = Field(default=None, gt=0)
    format_h_mm: int | None = Field(default=None, gt=0)
    nb_poses_l: int | None = Field(default=None, ge=1)
    nb_poses_h: int | None = Field(default=None, ge=1)
    forme_speciale: bool | None = None
    actif: bool | None = None
