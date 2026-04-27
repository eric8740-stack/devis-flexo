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
StatutComplexe = Literal["actif", "archive"]


class ComplexeBase(BaseModel):
    reference: str = Field(min_length=1, max_length=50)
    famille: FamilleComplexe
    face_matiere: str | None = Field(default=None, max_length=150)
    grammage_g_m2: int | None = Field(default=None, gt=0)
    adhesif_type: str | None = Field(default=None, max_length=50)
    prix_m2_eur: float = Field(gt=0)  # CRITIQUE pour le moteur de calcul S3
    fournisseur_id: int | None = None
    statut: StatutComplexe = "actif"
    commentaire: str | None = None


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
    grammage_g_m2: int | None = Field(default=None, gt=0)
    adhesif_type: str | None = Field(default=None, max_length=50)
    prix_m2_eur: float | None = Field(default=None, gt=0)
    fournisseur_id: int | None = None
    statut: StatutComplexe | None = None
    commentaire: str | None = None
