"""Modèle MachineRebobineuse — Sprint 16 Lot A (Module Rebobinage).

Parc des rebobineuses de l'imprimerie. Distinct des presses flexo
(`machine_imprimerie`) et de la table legacy `machine` qui sert au
cost_engine sacré. Conséquence : aucun risque de drift sur les
valeurs sacrées V1a 1449,09 € / V1b 1921,09 € — la rebobineuse est
une ligne ADDITIVE dans un service distinct (cf. Lot B).

Convention naming : table au singulier `machine_rebobineuse` (cohérent
avec `machine_imprimerie`, `cylindre_magnetique`, `porte_cliche`).
Multi-tenant : `entreprise_id` NOT NULL FK CASCADE indexed.

Saisie pilote : `vitesse_pratique_m_min` est la valeur RÉELLE saisie
par l'imprimeur (et non la vitesse catalogue constructeur, qui n'est
pas représentative en production). Même convention que
`machine_imprimerie.vitesse_pratique_m_min`.

Le mapping `mandrins_supportes` est une liste de diamètres mandrin en
mm (ex: `[25, 38, 76, 152]`). Le moteur de calcul du Lot B vérifie
que le diamètre demandé par le client appartient à cette liste avant
d'élire la rebobineuse.

Les `options` sont une liste de capabilities optionnelles (marquage
bobine, film protection inline, etc.) — JSON souple plutôt qu'une
table d'association pour rester KISS.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MachineRebobineuse(Base):
    """Rebobineuse du parc imprimerie (1..N par entreprise)."""

    __tablename__ = "machine_rebobineuse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identification
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    marque: Mapped[str | None] = mapped_column(String(50))
    modele: Mapped[str | None] = mapped_column(String(50))

    # Capacités physiques
    laize_max_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    diametre_max_mm: Mapped[int] = mapped_column(Integer, nullable=False)

    # Mandrins acceptés — liste de diamètres mm, ex: [25, 38, 76, 152]
    mandrins_supportes: Mapped[list[int] | None] = mapped_column(JSON)

    # Vitesse RÉELLE saisie par l'imprimeur (pas constructeur).
    # Pilote le calcul du temps de rebobinage au Lot B.
    vitesse_pratique_m_min: Mapped[int] = mapped_column(Integer, nullable=False)

    cout_horaire_eur: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    # Temps de changement de bobine (entre 2 bobines successives). Mn.
    temps_changement_bobine_min: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )

    # Options machine : ex ["marquage_bobine_inline", "film_protection_inline"]
    # Croisé au Lot B avec les exigences client (marquage_bobine_requis, etc.)
    options: Mapped[list[str] | None] = mapped_column(JSON)

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
