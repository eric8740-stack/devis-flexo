"""Modèle ConfigRoulage — Brief stratégique v2, Phase 1 (socle Stratégique).

Débits / configurations de roulage PAR ENTREPRISE et PAR FORMAT (onglet
Stratégique, section 3). Collection : plusieurs lignes par tenant (une par
format paramétré). Consommé en Phase 2 par le Poste 5 Roulage.
"""
from datetime import datetime
from decimal import Decimal
from typing import Final

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Modes de roulage supportés (section 3 du brief).
MODES_ROULAGE: Final = ("helicoidal", "alterne", "custom")


class ConfigRoulage(Base):
    """Débit/config de roulage par entreprise et par format (collection)."""

    __tablename__ = "config_roulage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Format paramétré (libellé libre : "A5", "A4", "100x80", ...).
    format_libelle: Mapped[str] = mapped_column(String(50), nullable=False)
    debit_mm_s: Mapped[int] = mapped_column(Integer, nullable=False, default=250)
    # helicoidal / alterne / custom (cf. MODES_ROULAGE).
    mode_roulage: Mapped[str] = mapped_column(
        String(20), nullable=False, default="helicoidal"
    )
    rebut_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("3.00")
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
