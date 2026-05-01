from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MachineBase(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    largeur_max_mm: int | None = Field(default=None, gt=0)
    # Sprint 7 Lot 7a — laize machine (largeur max imprimable mm). Requis,
    # consommé par le matcher cylindres pour valider la contrainte largeur
    # plaque ≤ laize_max - 2 × MARGE_SECURITE_LAIZE_MM.
    laize_max_mm: Decimal = Field(gt=0)
    vitesse_max_m_min: int | None = Field(default=None, gt=0)
    nb_couleurs: int | None = Field(default=None, ge=1, le=12)
    cout_horaire_eur: float | None = Field(default=None, ge=0)
    # Paramètres calcul S3
    vitesse_moyenne_m_h: int | None = Field(default=None, gt=0)
    duree_calage_h: float | None = Field(default=None, ge=0)
    # Sprint 9 v2 — soft delete uniformisé Boolean (refactor depuis statut String)
    actif: bool = True
    commentaire: str | None = None


class MachineRead(MachineBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class MachineCreate(MachineBase):
    """Body POST."""


class MachineUpdate(BaseModel):
    """Body PUT : tous les champs optionnels (partial update via exclude_unset)."""

    nom: str | None = Field(default=None, min_length=1, max_length=100)
    largeur_max_mm: int | None = Field(default=None, gt=0)
    laize_max_mm: Decimal | None = Field(default=None, gt=0)
    vitesse_max_m_min: int | None = Field(default=None, gt=0)
    nb_couleurs: int | None = Field(default=None, ge=1, le=12)
    cout_horaire_eur: float | None = Field(default=None, ge=0)
    vitesse_moyenne_m_h: int | None = Field(default=None, gt=0)
    duree_calage_h: float | None = Field(default=None, ge=0)
    actif: bool | None = None
    commentaire: str | None = None
