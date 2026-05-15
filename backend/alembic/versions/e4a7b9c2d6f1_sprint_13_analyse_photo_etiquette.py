"""Sprint 13 — Lot S13.E.2 : table analyse_photo_etiquette.

Crée la table de stockage des résultats d'analyse IA de photos
d'étiquettes (CdC § 03e). Une row par analyse, scopée tenant.

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
FK user.id et devis.id SET NULL (analyse peut survivre à la suppression
de l'auteur ou du devis rattaché — c'est un historique commercial).

Revision ID: e4a7b9c2d6f1
Revises: c9e5a3d8f4b2 (Sprint 13 Lot S13.F traceability tables)
Create Date: 2026-05-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4a7b9c2d6f1"
down_revision: Union[str, Sequence[str], None] = "c9e5a3d8f4b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analyse_photo_etiquette",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "devis_id",
            sa.Integer(),
            sa.ForeignKey("devis.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("photo_mime_type", sa.String(30), nullable=True),
        sa.Column("resultats_ia", sa.JSON(), nullable=False),
        sa.Column("niveau_confiance", sa.String(10), nullable=True),
        sa.Column("nombre_couleurs_distinctes", sa.Integer(), nullable=True),
        sa.Column("model_utilise", sa.String(60), nullable=True),
        sa.Column("erreur", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_analyse_photo_etiquette_entreprise_id",
        "analyse_photo_etiquette",
        ["entreprise_id"],
    )
    op.create_index(
        "ix_analyse_photo_etiquette_devis_id",
        "analyse_photo_etiquette",
        ["devis_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analyse_photo_etiquette_devis_id",
        table_name="analyse_photo_etiquette",
    )
    op.drop_index(
        "ix_analyse_photo_etiquette_entreprise_id",
        table_name="analyse_photo_etiquette",
    )
    op.drop_table("analyse_photo_etiquette")
