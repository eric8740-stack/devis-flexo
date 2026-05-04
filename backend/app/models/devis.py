"""Modèle Devis — persistance des calculs (Sprint 4 Lot 4a).

Stocke un devis calculé avec :
- Numéro auto format DEV-YYYY-NNNN (séquence annuelle)
- Statut brouillon/valide
- payload_input + payload_output en JSON pour flexibilité MVP
- Champs dénormalisés (ht_total, format, machine) pour la liste paginée
- En mode matching : cylindre_choisi_z + cylindre_choisi_nb_etiq

PK Integer autoincrement (homogène avec les 15 autres tables existantes,
pas UUID malgré le brief — convention projet figée Sprint 0).

JSON portable SQLite (dev) + Postgres (prod, JSONB via le dialect).
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Devis(Base):
    """Devis sauvegardé en base — résultat d'un calcul cost_engine + métadonnées."""

    __tablename__ = "devis"
    __table_args__ = (
        Index("ix_devis_date_creation_desc", "date_creation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Format DEV-YYYY-NNNN (ex: DEV-2026-0001), séquence annuelle générée
    # par numero_devis_service.generate_next_numero (Lot 4b).
    numero: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_modification: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    statut: Mapped[str] = mapped_column(
        Enum("brouillon", "valide", name="devis_statut_enum"),
        nullable=False,
        server_default="brouillon",
    )

    # Client lié optionnel — si supprimé, devis garde l'historique avec NULL.
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("client.id", ondelete="SET NULL"), index=True
    )

    # Snapshots JSON — flexibilité MVP, pas de migration si DevisInput/Output
    # évoluent (Sprint 8+ pourra normaliser si besoin).
    payload_input: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_output: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Mode + cylindre choisi (extraits du payload pour requêtes rapides).
    mode_calcul: Mapped[str] = mapped_column(String(10), nullable=False)
    cylindre_choisi_z: Mapped[int | None] = mapped_column(Integer)
    cylindre_choisi_nb_etiq: Mapped[int | None] = mapped_column(Integer)

    # Champs dénormalisés pour la liste paginée (évite parsing JSON par ligne).
    ht_total_eur: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    format_h_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    format_l_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machine.id"), nullable=False
    )
