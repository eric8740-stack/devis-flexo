"""Schémas Pydantic — CRUD /api/bobines (Module Stock S1, granularité A).

1 bobine = 1 ligne physique. L'emplacement est saisi sur 3 champs
`rangee`/`etage`/`position` et exposé calculé `emplacement` = "A.0.25".
`epaisseur_microns` est optionnel à la création (pré-rempli depuis la matière
si absent) puis éditable. `ml_initial` est figé à la création (= `ml_restant`
initial) ; seul `ml_restant` évolue ensuite.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


# Statuts S1 (le cycle s'enrichira avec les mouvements S2 / lien devis S3).
STATUTS_BOBINE = ("en_stock", "reserve", "consommee", "rebut")


class BobineCreate(BaseModel):
    """Body POST /api/bobines."""

    model_config = ConfigDict(extra="forbid")

    matiere_id: int = Field(gt=0)
    laize_mm: float = Field(gt=0, le=2000)
    # Optionnel : pré-rempli depuis la matière à la création si non fourni.
    epaisseur_microns: int | None = Field(None, ge=1, le=2000)
    ml_initial: int = Field(gt=0)
    rangee: str = Field(min_length=1, max_length=10)
    etage: int = Field(ge=0)
    position: int = Field(ge=0)
    statut: str = Field("en_stock", pattern="^(en_stock|reserve|consommee|rebut)$")


class BobineUpdate(BaseModel):
    """Body PATCH /api/bobines/{id} — champs partiels.

    `ml_initial` et `matiere_id` ne sont PAS modifiables (identité physique de
    la bobine). On édite l'emplacement, le métrage restant, l'épaisseur, le
    statut.
    """

    model_config = ConfigDict(extra="forbid")

    laize_mm: float | None = Field(None, gt=0, le=2000)
    epaisseur_microns: int | None = Field(None, ge=1, le=2000)
    ml_restant: int | None = Field(None, ge=0)
    rangee: str | None = Field(None, min_length=1, max_length=10)
    etage: int | None = Field(None, ge=0)
    position: int | None = Field(None, ge=0)
    statut: str | None = Field(None, pattern="^(en_stock|reserve|consommee|rebut)$")


class BobineOut(BaseModel):
    """Détail GET /api/bobines/{id} + retour POST/PATCH."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    matiere_id: int
    laize_mm: float
    epaisseur_microns: int | None = None
    ml_initial: int
    ml_restant: int
    rangee: str
    etage: int
    position: int
    statut: str
    date_creation: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emplacement(self) -> str:
        """Emplacement codé `rangee.etage.position` → ex. "A.0.25"."""
        return f"{self.rangee}.{self.etage}.{self.position}"
