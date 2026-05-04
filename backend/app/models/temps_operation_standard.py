from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TempsOperationStandard(Base):
    """Temps standard d'opérations flexo génériques (calage, démontage, ...).

    `categorie` attendue parmi : preparation / calage / production / demontage
    (validation côté Pydantic, colonne SQL souple — convention alignée sur
    `machine.statut`).
    """

    __tablename__ = "temps_operation_standard"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    libelle_operation: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True
    )
    minutes_standard: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("5.00")
    )
    categorie: Mapped[str | None] = mapped_column(String(50))
    ordre_affichage: Mapped[int] = mapped_column(Integer, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
