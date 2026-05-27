from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FamilleComplexe = Literal[
    "bopp",
    "pp",
    "pe",
    "pvc_vinyle",
    "thermique",
    "papier_couche",
    "papier_standard",
    "papier_epais",
    "papier_kraft",
    "papier_verge",
]


class ComplexeBase(BaseModel):
    reference: str = Field(min_length=1, max_length=50)
    famille: FamilleComplexe
    face_matiere: str | None = Field(default=None, max_length=150)
    # Lot 1 complexe enrichi : Numeric(5,1) en base — les films ont un grammage
    # de face décimal (45.5 g/m²). Exposé en float (même convention JSON que
    # prix_m2_eur : nombre, pas string Decimal).
    grammage_g_m2: float | None = Field(default=None, gt=0)
    adhesif_type: str | None = Field(default=None, max_length=50)
    prix_m2_eur: float = Field(gt=0)  # CRITIQUE pour le moteur de calcul S3
    fournisseur_id: int | None = None
    # Sprint 9 v2 — soft delete uniformisé Boolean (refactor depuis statut String)
    actif: bool = True
    commentaire: str | None = None

    # Lot 1 complexe enrichi — caractéristiques lues/filtrées par le moteur
    # d'optimisation (alignées sur la table `matiere`, pont matière↔complexe).
    epaisseur_microns: int | None = Field(default=None, gt=0)
    est_transparent: bool = False
    opacite_pct: float | None = Field(default=None, ge=0, le=100)
    sous_type: str | None = Field(default=None, max_length=50)
    certifications_sanitaires: list[str] | None = None
    certifications_env: list[str] | None = None


class ComplexeRead(ComplexeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class ComplexeCreate(ComplexeBase):
    pass


class ComplexeUpdate(BaseModel):
    reference: str | None = Field(default=None, min_length=1, max_length=50)
    famille: FamilleComplexe | None = None
    face_matiere: str | None = Field(default=None, max_length=150)
    grammage_g_m2: float | None = Field(default=None, gt=0)
    adhesif_type: str | None = Field(default=None, max_length=50)
    prix_m2_eur: float | None = Field(default=None, gt=0)
    fournisseur_id: int | None = None
    actif: bool | None = None
    commentaire: str | None = None
    # Lot 1 complexe enrichi
    epaisseur_microns: int | None = Field(default=None, gt=0)
    est_transparent: bool | None = None
    opacite_pct: float | None = Field(default=None, ge=0, le=100)
    sous_type: str | None = Field(default=None, max_length=50)
    certifications_sanitaires: list[str] | None = None
    certifications_env: list[str] | None = None
