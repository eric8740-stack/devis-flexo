"""Ajout de la table lot_production (Sprint 13 avenant — multi-lots).

Une commande devis peut être fractionnée en N lots de production avec
configurations différentes (cylindre, machine, poses, sens, matière,
quantité). Le moteur cost_engine reste inchangé et est appelé N fois
(une fois par lot) par l'agrégateur (cf. cost_engine_aggregator).

Multi-tenant : entreprise_id obligatoire, cascade depuis devis_id.

Revision ID: d3f1a8e6c5b2
Revises: c8f4d2b1e7a6
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d3f1a8e6c5b2"
down_revision: Union[str, Sequence[str], None] = "c8f4d2b1e7a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lot_production",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "devis_id",
            sa.Integer(),
            sa.ForeignKey("devis.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.Column(
            "cylindre_id",
            sa.Integer(),
            sa.ForeignKey("cylindre_magnetique.id"),
            nullable=False,
        ),
        sa.Column(
            "machine_id",
            sa.Integer(),
            sa.ForeignKey("machine_imprimerie.id"),
            nullable=False,
        ),
        sa.Column("nb_poses_dev", sa.Integer(), nullable=False),
        sa.Column("nb_poses_laize", sa.Integer(), nullable=False),
        sa.Column("sens_enroulement", sa.Integer(), nullable=False),
        sa.Column("quantite", sa.Integer(), nullable=False),
        sa.Column(
            "matiere_id",
            sa.Integer(),
            sa.ForeignKey("matiere.id"),
            nullable=False,
        ),
        sa.Column("intervalle_dev_reel_mm", sa.Numeric(5, 2), nullable=True),
        sa.Column("intervalle_laize_reel_mm", sa.Numeric(5, 2), nullable=True),
        sa.Column("largeur_plaque_mm", sa.Numeric(6, 2), nullable=True),
        sa.Column("score_optim", sa.Float(), nullable=True),
        sa.Column("cout_lot_ht_eur", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "devis_id", "ordre", name="uq_lot_production_devis_ordre"
        ),
    )
    op.create_index(
        "ix_lot_production_devis", "lot_production", ["devis_id"]
    )
    op.create_index(
        "ix_lot_production_entreprise", "lot_production", ["entreprise_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_lot_production_entreprise", table_name="lot_production")
    op.drop_index("ix_lot_production_devis", table_name="lot_production")
    op.drop_table("lot_production")
