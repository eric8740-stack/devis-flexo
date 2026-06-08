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

    # Phase 2 Lot 4a — tarifs P1/P3/P4/P6 migrés depuis TarifPoste vers
    # ConfigCouts (source unique par tenant). Defaults template neutres
    # comme Lot 3 ; les tenants existants (seed démo) sont alignés par
    # UPDATE legacy en migration.
    # P1 : marge de confort surface support, en mm (entier).
    marge_confort_roulage_mm: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )
    # P3a : prix d'un cliché par couleur.
    cliche_prix_couleur_eur: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("30.00")
    )
    # P3b : forfait nouvel outil + supplément par trace + facteur forme spé.
    # Le facteur est un MULTIPLICATEUR direct (1.30 = +30 %), pas un %.
    outil_base_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("150.00")
    )
    outil_par_trace_eur: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("40.00")
    )
    surcout_forme_speciale_facteur: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.30")
    )
    # P4 : forfait calage devis.
    calage_forfait_eur: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("180.00")
    )
    # P6 : prix m² finitions (€/m² fin → 4 décimales utiles).
    finitions_prix_m2_eur: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.1000")
    )

    # L1 (géométrie laize) — plancher de laize papier roulable (mm). La laize
    # papier déterministe ne descend jamais sous cette valeur (contrainte
    # presse/rebobineuse). Défaut NEUTRE = 0 en L1 (aucun plancher) ; câblage
    # métier réel à l'étape 2. NON consommé par P1 (cost_engine intouché).
    laize_mini_roulable_mm: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Lot back B — coût de refente (rebobinage finisseuse), ADDITIF hors des 7
    # postes. Taux horaire d'exploitation de la rebobineuse pour la refente +
    # % de gâche au raccord. Défauts NEUTRES = 0 → aucune ligne refente tant
    # que le tenant ne les configure pas (value-neutral, sacrés intouchés).
    cout_exploitation_rebobineuse_eur_h: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    gache_raccord_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0"), server_default="0"
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
