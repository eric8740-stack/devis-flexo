"""Modèle MachineImprimerie — Sprint 13 Lot S13.B.

Parc machines de l'imprimerie (presses flexo). Coexiste avec la table
existante `machine` (Sprint 2) sans la remplacer : `machine` continue
d'alimenter le moteur de coûts historique (V1a/V1b sacrés à préserver),
tandis que `machine_imprimerie` est dédiée au moteur d'optimisation
Sprint 13 et porte les vrais paramètres réalistes :
  - vitesse_pratique_m_min NOT NULL (SAISIE MANUELLE imprimerie, PAS
    la vitesse catalogue constructeur — qui reste indicative)
  - nb_groupes_couleurs (filtre dur règle 6 du moteur)
  - nb_postes_decoupe (1 ou 2, conditionne split-liner)
  - options JSON (UV, dorure_froid, sérigraphie_inline…)
  - cylindres_compatibles JSON (mapping machine → cylindres montables)

À terme (Sprint 14+) on pourra fusionner les 2 tables ou migrer
progressivement, mais le pari Sprint 13 = ne JAMAIS casser les sacrés
EXACT en gardant l'ancien moteur intact.

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
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


class MachineImprimerie(Base):
    __tablename__ = "machine_imprimerie"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identification machine
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    marque: Mapped[str | None] = mapped_column(String(50))
    modele: Mapped[str | None] = mapped_column(String(50))
    repere_court: Mapped[str | None] = mapped_column(String(20))

    # Laizes (mm) — physiques et utiles
    laize_totale_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    laize_utile_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    # Capacités machine — entrent dans le filtre dur règle 6 du moteur
    # (capacité groupes couleurs vs options du devis).
    nb_groupes_couleurs: Mapped[int | None] = mapped_column(Integer)
    nb_postes_decoupe: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )

    # Vitesses
    # vitesse_nominale_constructeur_m_min = info catalogue, indicatif seulement.
    # vitesse_pratique_m_min = saisie réelle imprimeur, pilote le calcul.
    vitesse_nominale_constructeur_m_min: Mapped[int | None] = mapped_column(Integer)
    vitesse_pratique_m_min: Mapped[int] = mapped_column(Integer, nullable=False)
    # V2 : surcharge par type de matière (ex: {"BOPP": 60, "PET": 40}).
    # JSON pour compat SQLite + PostgreSQL natif. None = pas de surcharge.
    vitesse_par_matiere: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    vitesse_max_tours_h: Mapped[int | None] = mapped_column(Integer)

    cout_horaire_eur: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    # Mapping cylindres compatibles : [{cyl_id, pc_format}] — JSON souple
    # plutôt qu'une table d'association pour rester KISS Sprint 13.
    cylindres_compatibles: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)

    # Options machine : ["UV", "dorure_froid", "serigraphie_inline", …]
    # → croisé avec options_fabrication.modules_speciaux_requis dans le moteur.
    options: Mapped[list[str] | None] = mapped_column(JSON)
    type_encre_supportee: Mapped[list[str] | None] = mapped_column(JSON)

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_acquisition: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
