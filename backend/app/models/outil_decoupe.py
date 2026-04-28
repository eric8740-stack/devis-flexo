from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OutilDecoupe(Base):
    """Catalogue des outils de découpe flexo (cylindres magnétiques équipés
    de plaques métalliques formées au format de l'étiquette).

    Sprint 5 simplifié : table catalogue de référence, sans coût stocké.
    Le calculateur P3b retourne 0 € pour tout outil existant (déjà amorti).
    Si nouvel outil → calculé à la volée à partir de nb_traces_complexite
    et forme_speciale dans le payload DevisInput, sans persistance.

    `actif` : soft delete (catalogue stable, on ne supprime pas l'historique).
    """

    __tablename__ = "outil_decoupe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    libelle: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    format_l_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    format_h_mm: Mapped[int] = mapped_column(Integer, nullable=False)

    nb_poses_l: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_poses_h: Mapped[int] = mapped_column(Integer, nullable=False)

    forme_speciale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
