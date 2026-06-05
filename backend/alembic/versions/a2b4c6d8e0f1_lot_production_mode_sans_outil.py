"""Lot back A — mode « format sans outil » sur lot_production.

Champs additifs (value-neutral, tout lot existant reste « avec outil ») :
  - `lot_production.mode_sans_outil` : Boolean NOT NULL `server_default=false`
    → impression pleine largeur + refente (pas d'outil de découpe).
  - `lot_production.laize_stock_mm` : Numeric(6,2) NULLABLE → laize bobine mère
    facturée par P1 en mode sans outil (NULL sinon).
  - `lot_production.cylindre_id` : passe NULLABLE (un lot sans outil n'a pas de
    cylindre). Altération Postgres uniquement ; SQLite (tests) recrée la table
    depuis le modèle déjà nullable via `create_all`.

Aucune donnée existante touchée. Réversible.

Revision ID: a2b4c6d8e0f1
Revises: f7a8b9c0d1e2
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a2b4c6d8e0f1"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lot_production",
        sa.Column(
            "mode_sans_outil",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "lot_production",
        sa.Column("laize_stock_mm", sa.Numeric(6, 2), nullable=True),
    )
    # cylindre_id → NULLABLE. SQLite ne supporte pas ALTER COLUMN ; en test la
    # table est créée depuis le modèle (déjà nullable) via create_all, donc on
    # n'altère que sous Postgres (scénario prod).
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "lot_production",
            "cylindre_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "lot_production",
            "cylindre_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
    op.drop_column("lot_production", "laize_stock_mm")
    op.drop_column("lot_production", "mode_sans_outil")
