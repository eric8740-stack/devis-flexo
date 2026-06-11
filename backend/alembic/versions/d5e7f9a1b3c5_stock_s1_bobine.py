"""Module Stock S1 — table `bobine` (1 ligne = 1 bobine physique, granularité A).

Table ADDITIVE (ne touche aucune table existante) : suivi du stock physique de
bobines, scopé tenant. FK `entreprise_id` (CASCADE) + `matiere_id` (RESTRICT par
défaut). Emplacement codé sur rangee/etage/position (affiché `A.0.25` côté API).

DDL natif `op.create_table` (pas de batch_alter_table) — cf. leçon migration F :
ne jamais recréer une table parente FK en batch SQLite. Ici on ne fait que créer
une table neuve, donc aucun risque ; les colonnes FK pointent vers entreprise /
matiere existantes.

Reversible : drop_table("bobine").

Revision ID: d5e7f9a1b3c5
Revises: c4d6e8f0a1b3
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d5e7f9a1b3c5"
down_revision: Union[str, Sequence[str], None] = "c4d6e8f0a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bobine",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entreprise_id", sa.Integer(), nullable=False),
        sa.Column("matiere_id", sa.Integer(), nullable=False),
        sa.Column("laize_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("epaisseur_microns", sa.Integer(), nullable=True),
        sa.Column("ml_initial", sa.Integer(), nullable=False),
        sa.Column("ml_restant", sa.Integer(), nullable=False),
        sa.Column("rangee", sa.String(length=10), nullable=False),
        sa.Column("etage", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "statut",
            sa.String(length=20),
            nullable=False,
            server_default="en_stock",
        ),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entreprise_id"], ["entreprise.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["matiere_id"], ["matiere.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bobine_entreprise_id"), "bobine", ["entreprise_id"], unique=False
    )
    op.create_index(
        op.f("ix_bobine_matiere_id"), "bobine", ["matiere_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_bobine_matiere_id"), table_name="bobine")
    op.drop_index(op.f("ix_bobine_entreprise_id"), table_name="bobine")
    op.drop_table("bobine")
