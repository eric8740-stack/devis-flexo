from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OperationFinition(Base):
    """Opération de finition réalisée en interne (vernis, laminage, dorure...)."""

    __tablename__ = "operation_finition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    nom: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # m2 / ml / unite / millier
    unite_facturation: Mapped[str] = mapped_column(String(20), nullable=False)

    cout_unitaire_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    temps_minutes_unite: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

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
