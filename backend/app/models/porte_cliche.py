"""Modèle PorteCliche — Brief #29 (paramètres parc).

Sémantique métier : un porte-cliché (sleeve / plate mounting cylinder) est
le support physique monté sur le cylindre porteur machine. Il porte le
cliché flexo. Distinct du `CylindreMagnetique` qui représente le développé
(nb_dents × 3.175 mm).

Réutilisable d'un job à l'autre, indépendant du développé. Catalogue par
imprimerie (tenant), multi-tenant strict via `entreprise_id` (CASCADE).
Référence unique par entreprise (UniqueConstraint).

Soft delete uniformisé (`actif: bool`, convention Sprint 9 v2) — pas de
suppression dure pour préserver d'éventuelles FK historiques futures.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PorteCliche(Base):
    __tablename__ = "porte_cliche"
    __table_args__ = (
        UniqueConstraint(
            "entreprise_id", "reference", name="uq_porte_cliche_reference_entreprise"
        ),
        Index("ix_porte_cliche_entreprise", "entreprise_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12-C multi-tenant — scope par entreprise.
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Référence interne (ex: "PC-220", "Sleeve-330"). Unique par entreprise.
    reference: Mapped[str] = mapped_column(String(50), nullable=False)

    # Métadonnées libres pour faciliter l'inventaire physique.
    marque: Mapped[str | None] = mapped_column(String(80))
    modele: Mapped[str | None] = mapped_column(String(80))

    # Caractéristiques techniques.
    laize_utile_mm: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False
    )
    diametre_interieur_mm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    # Matière du sleeve (polyuréthane / carbone / acier / autre — texte libre).
    matiere: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
