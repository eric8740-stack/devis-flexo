"""Modèle ConfigCouts — Brief stratégique v2, Phase 1 (socle Stratégique).

Coûts variables/fixes + marges configurés PAR ENTREPRISE (onglet Stratégique,
section 4). Une seule ligne par tenant (singleton scopé entreprise_id, unique).

Objectif SaaS : sortir des données ICE hardcodées — chaque entreprise pose
ses propres coûts. Valeurs par défaut neutres (template) à l'onboarding,
ajustables. Le refacto du moteur (Phase 2) consommera ces valeurs au lieu
des seeds ICE.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConfigCouts(Base):
    """Coûts & marges par entreprise (singleton : 1 ligne par tenant)."""

    __tablename__ = "config_couts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Singleton par tenant : unique (1 config coûts par entreprise).
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Coûts variables (€/heure)
    cout_exploitation_machine_eur_h: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("50.00")
    )
    cout_operateur_eur_h: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("25.00")
    )
    cout_energies_eur_h: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("3.50")
    )

    # Coûts fixes (€/mois)
    cout_fixe_atelier_eur_mois: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("2500.00")
    )
    cout_fixe_maintenance_eur_mois: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("800.00")
    )

    # Marges & buffers (%)
    marge_standard_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("35.00")
    )
    buffer_rebut_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("2.50")
    )
    buffer_setup_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.00")
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
