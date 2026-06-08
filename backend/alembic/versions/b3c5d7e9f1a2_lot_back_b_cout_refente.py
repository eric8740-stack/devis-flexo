"""Lot back B — coût de refente (rebobinage) : champs config + nb_filles_force.

Champs additifs (value-neutral, défauts 0/NULL → aucune ligne refente tant que
non configuré) :
  - `config_couts.cout_exploitation_rebobineuse_eur_h` : Numeric(10,2) NOT NULL
    `server_default=0` — taux horaire refente.
  - `config_couts.gache_raccord_pct` : Numeric(5,2) NOT NULL `server_default=0`
    — % de gâche au raccord.
  - `lot_production.nb_filles_force` : Integer NULLABLE — override opérateur du
    nb de filles de refente (source du nb_filles résolu, ≠ nb_poses_laize).

Aucune donnée existante touchée. Réversible.

Revision ID: b3c5d7e9f1a2
Revises: a2b4c6d8e0f1
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b3c5d7e9f1a2"
down_revision: Union[str, Sequence[str], None] = "a2b4c6d8e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "config_couts",
        sa.Column(
            "cout_exploitation_rebobineuse_eur_h",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "gache_raccord_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "lot_production",
        sa.Column("nb_filles_force", sa.Integer(), nullable=True),
    )

    # Rétro-fix SQLite : la migration lot A (a2b4c6d8e0f1) a passé
    # `lot_production.cylindre_id` en NULLABLE uniquement sous Postgres (ALTER
    # COLUMN non supporté par SQLite → sauté). Les bases SQLite migrées (dev /
    # tests locaux) l'ont gardé NOT NULL, ce qui empêche un lot « sans outil »
    # (cylindre_id NULL). On le corrige ici via batch (recrée la table). Sur
    # Postgres c'est déjà nullable → no-op explicite (guard dialecte).
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("lot_production") as batch_op:
            batch_op.alter_column(
                "cylindre_id", existing_type=sa.Integer(), nullable=True
            )


def downgrade() -> None:
    op.drop_column("lot_production", "nb_filles_force")
    op.drop_column("config_couts", "gache_raccord_pct")
    op.drop_column("config_couts", "cout_exploitation_rebobineuse_eur_h")
