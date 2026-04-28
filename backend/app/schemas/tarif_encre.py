from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TarifEncreBase(BaseModel):
    type_encre: str = Field(min_length=1, max_length=50)
    libelle: str = Field(min_length=1, max_length=100)
    prix_kg_defaut: Decimal
    prix_kg_min: Decimal | None = None
    prix_kg_max: Decimal | None = None
    ratio_g_m2_couleur: Decimal = Decimal("2.000")
    actif: bool = True


class TarifEncreRead(TarifEncreBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class TarifEncreCreate(TarifEncreBase):
    """Body POST."""


class TarifEncreUpdate(BaseModel):
    type_encre: str | None = Field(default=None, min_length=1, max_length=50)
    libelle: str | None = Field(default=None, min_length=1, max_length=100)
    prix_kg_defaut: Decimal | None = None
    prix_kg_min: Decimal | None = None
    prix_kg_max: Decimal | None = None
    ratio_g_m2_couleur: Decimal | None = None
    actif: bool | None = None
