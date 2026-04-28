from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OutilDecoupeRead(BaseModel):
    """Sortie API GET /api/outils — utilisée par le select frontend Lot 5d."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    libelle: str
    format_l_mm: int
    format_h_mm: int
    nb_poses_l: int
    nb_poses_h: int
    forme_speciale: bool
    actif: bool
    date_creation: datetime
