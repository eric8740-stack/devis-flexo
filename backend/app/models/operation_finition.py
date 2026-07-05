from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OperationFinition(Base):
    """Opération de finition réalisée en interne (vernis, laminage, dorure...)."""

    __tablename__ = "operation_finition"
    __table_args__ = (
        # Blindage pilote (audit 05/07/2026 E2) — UNIQUE composite scopé
        # tenant (migration r7t2u9w4x1z6).
        UniqueConstraint(
            "entreprise_id", "nom", name="uq_operation_finition_entreprise_nom"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nom: Mapped[str] = mapped_column(String(100), nullable=False)

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
