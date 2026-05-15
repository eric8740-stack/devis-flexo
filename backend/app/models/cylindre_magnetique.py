"""Modèle CylindreMagnetique — Sprint 13 Lot S13.B.

Catalogue des cylindres magnétiques disponibles dans le parc d'une
imprimerie. Chaque cylindre est défini par son **développé** (circonférence
en mm) et sert au moteur d'optimisation pour calculer la pose des
étiquettes.

ICE a 19 développés standards qui serviront de catalogue par défaut au
moment de l'onboarding express (Lot S13.C) : 72, 80, 82, 84, 86, 88, 90,
92, 96, 98, 103, 104, 112, 116, 128, 132, 134, 136, 144 mm.

Stock par format de plaque-cylindre (nb_pc_*) : utilité opérationnelle
(combien d'exemplaires physiques au format 10p / 13p / 2200 / P5).
Pas requis pour le moteur, mais facilite la planification atelier.

Multi-tenant : entreprise_id NOT NULL FK CASCADE (Sprint 12-C convention).
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
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


class CylindreMagnetique(Base):
    __tablename__ = "cylindre_magnetique"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12-C multi-tenant — scope par entreprise.
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Développé = circonférence du cylindre en mm. Champ clé pour le moteur
    # d'optimisation (détermine la pose dev et l'éligibilité effet banane).
    developpe_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    # Repère interne lié à une machine (ex: "2200 #3"). Facultatif.
    machine_repere: Mapped[str | None] = mapped_column(String(20))

    # Inventaire physique par format de plaque-cylindre (PC). 4 formats
    # courants ICE. Tous default 0 = pas d'exemplaire au stock pour ce format.
    nb_pc_10p: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_pc_13p: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_pc_2200: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_pc_p5: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_inventaire: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
