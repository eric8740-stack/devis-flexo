"""Sprint 15 Lot 3 — ajout table bat_reference (FlexoCheck).

Un BAT (Bon À Tirer) par devis. 1 row vivante par devis_id (UNIQUE) ; le
ré-upload remplace en place. Stockage des métadonnées seulement — le
binaire reste sur Volume Railway via photo_storage, et un futur sprint
basculera sur Vercel Blob / R2.

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
devis_id NOT NULL FK CASCADE + UNIQUE.

Aucune table existante touchée. Création from scratch → sûre sur prod
(pas de backfill `entreprise_id=1`, pas de FK posée sur une table peuplée).

Revision ID: m4f9b6e3a8c1
Revises: l3e8a5c7d2f1
Create Date: 2026-05-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "m4f9b6e3a8c1"
down_revision: Union[str, Sequence[str], None] = "l3e8a5c7d2f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bat_reference",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "devis_id",
            sa.Integer(),
            sa.ForeignKey("devis.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bat_url", sa.Text(), nullable=False),
        sa.Column("image_key", sa.String(120), nullable=True),
        sa.Column("bat_filename", sa.String(255), nullable=True),
        sa.Column("bat_mime_type", sa.String(50), nullable=False),
        sa.Column("bat_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "bat_uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "bat_date_validation", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("bat_valide_par", sa.String(200), nullable=True),
        sa.UniqueConstraint("devis_id", name="uq_bat_reference_devis"),
    )
    op.create_index(
        "ix_bat_reference_entreprise", "bat_reference", ["entreprise_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_bat_reference_entreprise", table_name="bat_reference")
    op.drop_table("bat_reference")
