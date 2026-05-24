"""Sprint 15 Lot 3 — ajout colonne premier_tirage_image_key sur controle_bat.

Sert au scope sécurisé de `GET /api/flexocheck/blobs/{image_key}` : sans
cette colonne il faudrait parser l'URL `premier_tirage_url` pour
retrouver la clé locale, fragile aux changements de format d'URL.

Nullable + sans backfill : aucune row existante (table créée par
l3e8a5c7d2f1, jamais peuplée hors tests Lot 1).

Revision ID: n5g8c7d4e2b9
Revises: m4f9b6e3a8c1
Create Date: 2026-05-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "n5g8c7d4e2b9"
down_revision: Union[str, Sequence[str], None] = "m4f9b6e3a8c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("controle_bat") as batch_op:
        batch_op.add_column(
            sa.Column("premier_tirage_image_key", sa.String(120), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("controle_bat") as batch_op:
        batch_op.drop_column("premier_tirage_image_key")
