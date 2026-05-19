"""Modèle PorteCliche — refonte métier Brief #30.

Un porte-cliché en flexo étroite est un cylindre métallique avec engrenage
**dent par dent identique** au cylindre magnétique. On y colle adhésif +
cliché polymère. Synchronisation mécanique par engrenage entre le porte-
cliché et le cylindre magnétique → 1 PC montable par couple (machine ×
cyl mag), N exemplaires identiques = nombre de couleurs de la machine.

Cardinalité métier : unique par (entreprise_id, machine_id, cylindre_id).
La `quantite` représente combien d'exemplaires identiques du PC sont
montés simultanément sur la machine (default = nb_groupes_couleurs de
la machine).

Historique :
- Brief #29 (PR #29) : modèle erroné basé sur sleeves modernes (marque/
  modele/laize_utile_mm/matiere) — interprétation métier incorrecte.
- Brief #30 (cette refonte) : schéma corrigé. Migration drop l'ancienne
  table avec ses 3 seeds absurdes (PC-220 Rotec, PC-330 DuPont Cyrel
  Fast, PC-410 Flint) et recrée le bon schéma + reseed 21 cyl × 3
  machines actives en compte demo.

Convention FK (cohérente avec LotProduction Sprint 13) :
  - `machine_id` → `machine_imprimerie.id` (table d'optim Sprint 13)
  - `cylindre_id` → `cylindre_magnetique.id`
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PorteCliche(Base):
    """Porte-cliché (cylindre engrenage synchronisé au cyl magnétique).

    Unique par (entreprise_id, machine_id, cylindre_id). Soft delete via
    `actif=False` (préserve toute FK historique future).
    """

    __tablename__ = "porte_cliche"
    __table_args__ = (
        Index("ix_porte_cliche_entreprise", "entreprise_id"),
        UniqueConstraint(
            "entreprise_id",
            "machine_id",
            "cylindre_id",
            name="uq_porte_cliche_entreprise_machine_cyl",
        ),
        CheckConstraint("quantite >= 0", name="ck_porte_cliche_quantite_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machine_imprimerie.id"), nullable=False
    )
    cylindre_id: Mapped[int] = mapped_column(
        ForeignKey("cylindre_magnetique.id"), nullable=False
    )

    # Nombre d'exemplaires identiques du PC montés simultanément sur la
    # machine. Default applicatif côté CRUD = machine.nb_groupes_couleurs.
    quantite: Mapped[int] = mapped_column(Integer, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)

    actif: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
