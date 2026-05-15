"""Modèle OptionFabrication — Sprint 13 Lot S13.B.

Catalogue des 20 options de fabrication (Impression / Finition / Données
variables / Sécurité / Découpe / Construction / Intelligent / Encre
spéciale) — cf. INSTRUCTIONS section 7 + CdC.

Chaque option porte :
  - sa consommation ressources machine (groupes_couleurs_requis,
    modules_speciaux_requis JSON) — alimente le filtre dur règle 6 du
    moteur d'optimisation
  - ses impacts production (coef_vitesse_impact, coef_gache_impact,
    ajoute_temps_calage_min) — cumulés multiplicativement dans le moteur
  - sa tarification (forfait_eur OU prix_au_m2_eur OU prix_au_mille_eur)
  - un flag est_silhouette_auto qui déclenche le calcul silhouette
    automatique (microperf, prédécoupe, etc.)

Convention `entreprise_id` :
  - NULL = option du catalogue global (livrée par défaut au seed Sprint 13)
  - NOT NULL = override imprimerie (l'imprimeur a redéfini ses propres
    coefs en partant du global). On gère le merge dans le moteur.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OptionFabrication(Base):
    __tablename__ = "option_fabrication"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ⚠️ Nullable : NULL = catalogue global (defaults Sprint 13), NOT NULL
    # = override imprimerie. Le moteur fusionne (override > global) dans
    # l'ordre de priorité.
    entreprise_id: Mapped[int | None] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Identification
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    libelle: Mapped[str] = mapped_column(String(200), nullable=False)
    categorie: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    # Consommation ressources machine (filtre dur règle 6 du moteur)
    ajoute_cliches: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    ajoute_couleurs: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    ajoute_outils_decoupe: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    groupes_couleurs_requis: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    # Modules machine requis (ex: ["retournement_laize", "hot_stamping"])
    # — croisé avec machine_imprimerie.options dans le filtre dur règle 6.
    modules_speciaux_requis: Mapped[list[str] | None] = mapped_column(JSON)
    est_silhouette_auto: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Impacts production (cumul multiplicatif dans le moteur d'optimisation)
    ajoute_temps_calage_min: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    coef_vitesse_impact: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )
    coef_gache_impact: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )

    # Tarification — 3 modes au choix (un seul renseigné typiquement)
    forfait_eur: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    prix_au_m2_eur: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    prix_au_mille_eur: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    cout_consommable_eur: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
