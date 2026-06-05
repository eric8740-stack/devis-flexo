"""L1 géométrie laize — bord latéral surchargeable + plancher laize roulable.

Prépare le rebasage P1 sur la laize papier réelle (étape 2) SANS l'exécuter :
P1 reste INTOUCHÉ (cost_engine non modifié). Ce lot rend la laize papier
déterministe et surchargeable, value-neutral sur les sacrés (V1a / tripwire).

Champs additifs :
  - `config_couts.laize_mini_roulable_mm` : plancher laize papier (mm), NOT
    NULL `server_default="0"` (neutre en L1 → aucun plancher).
  - `lot_production.bord_lateral_mm` : bord latéral symétrique surchargeable
    (mm), NULLABLE → défaut = `entreprise.chute_laterale_min_mm` (comportement
    actuel préservé). Concept séparé des lacets.

Aucune donnée existante touchée. Réversible.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "config_couts",
        sa.Column(
            "laize_mini_roulable_mm",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "lot_production",
        sa.Column("bord_lateral_mm", sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lot_production", "bord_lateral_mm")
    op.drop_column("config_couts", "laize_mini_roulable_mm")
