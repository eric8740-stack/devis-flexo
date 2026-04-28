from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CorrespondanceLaizeMetrageBase(BaseModel):
    laize_mm: int = Field(gt=0)
    metrage_metres: int = Field(gt=0)


class CorrespondanceLaizeMetrageRead(CorrespondanceLaizeMetrageBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class CorrespondanceLaizeMetrageCreate(CorrespondanceLaizeMetrageBase):
    """Body POST."""


class CorrespondanceLaizeMetrageUpdate(BaseModel):
    laize_mm: int | None = Field(default=None, gt=0)
    metrage_metres: int | None = Field(default=None, gt=0)
