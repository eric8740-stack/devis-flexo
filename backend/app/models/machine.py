from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Machine(Base):
    """Presse flexo de l'imprimerie. Sert au calcul du temps de roulage (S3)."""

    __tablename__ = "machine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    nom: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    largeur_max_mm: Mapped[int | None] = mapped_column(Integer)
    vitesse_max_m_min: Mapped[int | None] = mapped_column(Integer)
    nb_couleurs: Mapped[int | None] = mapped_column(Integer)
    cout_horaire_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # actif / inactif / maintenance — validé côté Pydantic, colonne SQL souple
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="actif")

    commentaire: Mapped[str | None] = mapped_column(Text)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
