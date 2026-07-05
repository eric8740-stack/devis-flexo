"""Lot D1 — `lot_production.changement_outil_cliche` (calage lié au montage).

Ajoute le flag pilotant le comptage des calages : `nb_calages = 1 +
nb_lots(changement_outil_cliche=True)`. Le 1er lot porte le calage du montage ;
un lot ne déclenche un calage supplémentaire que sur un VRAI changement
d'outil/cliché (pas un simple changement de bobine mère).

Additif, value-neutral : `server_default false` → tous les lots existants
gardent le comportement « pas de calage supplémentaire » (un devis multi-lots
de même montage facture 1 calage, comme la dédup signature qu'il remplace).

DDL natif `op.add_column` (PAS batch_alter_table) : `lot_production` est une
table PARENT (FK depuis aucun enfant côté stock, mais on applique la leçon F par
prudence — le recreate batch SQLite avec PRAGMA foreign_keys=ON viderait une
table FK-référencée). SQLite ≥3.35 + Postgres : ADD COLUMN natif, in-place.

Reversible : drop_column.

Revision ID: f7a9c1e3d5b7
Revises: e6f8a0b2c4d6
Create Date: 2026-06-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f7a9c1e3d5b7"
down_revision: Union[str, Sequence[str], None] = "r7t2u9w4x1z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lot_production",
        sa.Column(
            "changement_outil_cliche",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("lot_production", "changement_outil_cliche")
