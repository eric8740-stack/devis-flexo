"""Module Stock S2 — table `mouvement_stock` (journal d'audit des mouvements).

Table ADDITIVE : journal append-only des mouvements (entree / sortie /
inventaire) ajustant `bobine.ml_restant` transactionnellement. FK `entreprise_id`
(CASCADE), `bobine_id` (CASCADE — la suppression dure d'une bobine emporte son
historique), `devis_id` (SET NULL, renseigné en S3).

DDL natif `op.create_table` (cf. leçon migration F : pas de batch sur table
parente). Création d'une table neuve → aucun risque FK.

Reversible : drop_table("mouvement_stock").

Revision ID: e6f8a0b2c4d6
Revises: d5e7f9a1b3c5
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e6f8a0b2c4d6"
down_revision: Union[str, Sequence[str], None] = "d5e7f9a1b3c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mouvement_stock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entreprise_id", sa.Integer(), nullable=False),
        sa.Column("bobine_id", sa.Integer(), nullable=False),
        sa.Column("devis_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("ml", sa.Integer(), nullable=False),
        sa.Column("ml_avant", sa.Integer(), nullable=False),
        sa.Column("ml_apres", sa.Integer(), nullable=False),
        sa.Column("motif", sa.String(length=200), nullable=True),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entreprise_id"], ["entreprise.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["bobine_id"], ["bobine.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["devis_id"], ["devis.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mouvement_stock_entreprise_id"),
        "mouvement_stock",
        ["entreprise_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mouvement_stock_bobine_id"),
        "mouvement_stock",
        ["bobine_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mouvement_stock_devis_id"),
        "mouvement_stock",
        ["devis_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_mouvement_stock_devis_id"), table_name="mouvement_stock"
    )
    op.drop_index(
        op.f("ix_mouvement_stock_bobine_id"), table_name="mouvement_stock"
    )
    op.drop_index(
        op.f("ix_mouvement_stock_entreprise_id"), table_name="mouvement_stock"
    )
    op.drop_table("mouvement_stock")
