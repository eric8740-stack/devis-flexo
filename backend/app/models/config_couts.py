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

    # Phase 2 / Lot 4a — 7 constantes auparavant rangées comme rows sur
    # `tarif_poste` (sprint 9 v2) consommées par P1/P3/P4/P6 ; désormais
    # scopées tenant. server_default = baseline marché agrégée (les
    # valeurs spécifiques au tenant démo sont posées par la migration
    # x8m1h2j6f0g4 UPDATE entreprise_id=1, pas par ce default). Pattern
    # nullable=False + Decimal default identique au socle Phase 1.
    marge_confort_roulage_mm: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10  # P1 — marge bobine fille (mm)
    )
    cliche_prix_couleur_eur: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("50.00")  # P3a
    )
    outil_base_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("300.00")  # P3b base
    )
    outil_par_trace_eur: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("60.00")  # P3b par trace
    )
    # NB : `_facteur` (multiplicateur ∈ [1.0, 2.0], typique 1.40 démo), pas
    # `_pct`. Le nom historique `surcout_forme_speciale_pct` côté tarif_poste
    # était trompeur : la valeur n'est PAS un pourcentage (× 1.40), c'est un
    # multiplicateur. Le rename Lot 4a corrige la sémantique.
    surcout_forme_speciale_facteur: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.50")  # P3b multiplicateur
    )
    calage_forfait_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("250.00")  # P4
    )
    finitions_prix_m2_eur: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.1500")  # P6
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
