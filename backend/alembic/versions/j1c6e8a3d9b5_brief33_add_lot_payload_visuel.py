"""Brief #33 — ajout colonne payload_visuel sur lot_production.

Snapshot JSON des champs visuels d'un candidat moteur optim (laize papier,
liner, chute latérale, diamètre bobine, lacets, rotations). Permet de
rejouer SchemaImplantation Vue A/B/C par lot dans DevisResultMultiLots
sans recalcul cost_engine, et de re-hydrater le store en mode édition
(/optimisation?devis_id=X) avec un visuel fidèle.

Nullable pour compat rétroactive avec les lots créés avant ce brief —
côté UI on retombe sur le placeholder si la colonne est NULL.

Revision ID: j1c6e8a3d9b5
Revises: i9d5f8a4c7b2
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "j1c6e8a3d9b5"
down_revision: Union[str, Sequence[str], None] = "i9d5f8a4c7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # JSONB sur Postgres, JSON sur SQLite (tests) — batch_alter_table gère
    # la diff dialect (sqlite recrée la table). `using_jsonb` côté Postgres
    # via postgresql.JSONB().with_variant(sa.JSON, "sqlite").
    with op.batch_alter_table("lot_production") as batch_op:
        batch_op.add_column(
            sa.Column(
                "payload_visuel",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(
                    sa.JSON(), "sqlite"
                ),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("lot_production") as batch_op:
        batch_op.drop_column("payload_visuel")
