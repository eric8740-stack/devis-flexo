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
from typing import TYPE_CHECKING

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.lot_production import LotProduction


class Devis(Base):
    """Devis sauvegardé en base — résultat d'un calcul cost_engine + métadonnées."""

    __tablename__ = "devis"
    __table_args__ = (
        Index("ix_devis_date_creation_desc", "date_creation"),
        # Fix 409 (migration y9n2i3g7d5f0) — UNIQUE scope tenant :
        # un meme numero peut exister chez deux entreprises differentes.
        # L'index sert aussi a `generate_next_numero` qui filtre par
        # (entreprise_id, numero LIKE 'DEV-YYYY-%').
        Index(
            "ix_devis_entreprise_id_numero",
            "entreprise_id",
            "numero",
            unique=True,
        ),
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
    # L'unicite est portee par `ix_devis_entreprise_id_numero` (composite,
    # scope tenant) declaree dans __table_args__ -- pas par cette colonne.
    numero: Mapped[str] = mapped_column(String(20), nullable=False)

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
    # Sprint 16 fix chiffrage : nullable depuis la migration t4i6d8b2a9c5.
    # Un devis dont le chiffrage auto a échoué (ex: matière non reliée à un
    # complexe de coût) est créé en "chiffrage incomplet" avec ht_total_eur
    # NULL + payload_output.chiffrage_auto_erreur — jamais un 0 € trompeur.
    ht_total_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    format_h_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    format_l_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machine.id"), nullable=False
    )

    # Brief #32 commit 2 — réduction commerciale (0..100 %), appliquée
    # par-dessus le prix_vente_ht_eur calculé par le cost_engine. Le
    # champ ne change pas `ht_total_eur` (qui reste le brut) — l'UI
    # affiche les deux pour transparence (brut + après remise).
    reduction_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default="0", default=Decimal(0)
    )

    # Sprint 14 Lot 1 — brief client unifié. Ces 5 champs caractérisent
    # la livraison finale au client (commune à tous les lots d'un devis) :
    # quantité par rouleau, contrainte machine cliente, type d'entrée
    # fichier et conditions de stockage (servent à la déduction adhésif).
    # Tous rétro-compatibles : nullable ou server_default pour ne pas
    # casser les devis existants.
    nb_etiquettes_par_rouleau: Mapped[int | None] = mapped_column(Integer)
    diametre_max_bobine_mm: Mapped[int | None] = mapped_column(Integer)
    nb_fronts_sortie: Mapped[int | None] = mapped_column(
        Integer, server_default="1", default=1
    )
    type_entree_fichier: Mapped[str] = mapped_column(
        Enum(
            "vierge",
            "bat_pro_fourni",
            "a_designer",
            name="devis_type_entree_fichier_enum",
        ),
        nullable=False,
        server_default="a_designer",
        default="a_designer",
    )
    conditions_stockage: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )

    # Sprint 13 avenant — lots de production multi-lots (N lots par devis).
    # Cascade delete : la suppression d'un devis emporte ses lots.
    lots_production: Mapped[list["LotProduction"]] = relationship(
        "LotProduction",
        back_populates="devis",
        cascade="all, delete-orphan",
        order_by="LotProduction.ordre",
    )
