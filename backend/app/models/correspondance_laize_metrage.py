from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CorrespondanceLaizeMetrage(Base):
    """Mapping laize (mm) → métrage standard (m) — paramétrable par l'imprimerie.

    Convention projet : toutes les dimensions linéaires sont en mm
    (laize, développement, intervalles, marges).
    """

    __tablename__ = "correspondance_laize_metrage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    laize_mm: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    metrage_metres: Mapped[int] = mapped_column(Integer, nullable=False)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
