"""Brief #32 — ajout colonne reduction_pct sur devis.

Réduction commerciale (0..100 %) appliquée par-dessus prix_vente_ht_eur
calculé par cost_engine. Ne modifie pas `ht_total_eur` (brut) — l'UI
calcule et affiche le prix après réduction séparément.

Default 0 (pas de remise par défaut) pour rester rétro-compatible avec
les devis existants. Numeric(5, 2) suffit pour 0.00 à 100.00.

Revision ID: i9d5f8a4c7b2
Revises: h7d2e6f4a9c3
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "i9d5f8a4c7b2"
down_revision: Union[str, Sequence[str], None] = "h7d2e6f4a9c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres supporte directement add_column avec server_default.
    # SQLite (tests) le supporte aussi via batch_alter_table.
    with op.batch_alter_table("devis") as batch_op:
        batch_op.add_column(
            sa.Column(
                "reduction_pct",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("devis") as batch_op:
        batch_op.drop_column("reduction_pct")
