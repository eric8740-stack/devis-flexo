"""Modèle ConfigChangements — Brief stratégique v2, Phase 1 (socle Stratégique).

Durées + coûts des changements (couleur, format, nettoyage) configurés PAR
ENTREPRISE (onglet Stratégique, section 5). Une seule ligne par tenant.

Consommé en Phase 2 par le moteur (calage/roulage) au lieu des seeds ICE.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConfigChangements(Base):
    """Changements (couleur/format/nettoyage) par entreprise (singleton)."""

    __tablename__ = "config_changements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Changement couleur
    changement_couleur_duree_min: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15
    )
    changement_couleur_cout_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("12.50")
    )

    # Changement format
    changement_format_duree_min: Mapped[int] = mapped_column(
        Integer, nullable=False, default=25
    )
    changement_format_cout_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("18.00")
    )

    # Nettoyage machine
    nettoyage_duree_min: Mapped[int] = mapped_column(
        Integer, nullable=False, default=45
    )
    nettoyage_cout_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("35.00")
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
