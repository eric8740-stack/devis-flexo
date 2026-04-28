"""Sprint 3 rename laize_cm to laize_mm

Revision ID: 381843cf212d
Revises: 716126871532
Create Date: 2026-04-28 09:36:50.635251

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '381843cf212d'
down_revision: Union[str, Sequence[str], None] = '716126871532'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch_alter_table : indispensable pour SQLite (recrée la table en
    # arrière-plan), no-op cosmétique pour Postgres.
    with op.batch_alter_table("correspondance_laize_metrage") as batch_op:
        batch_op.alter_column("laize_cm", new_column_name="laize_mm")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("correspondance_laize_metrage") as batch_op:
        batch_op.alter_column("laize_mm", new_column_name="laize_cm")
