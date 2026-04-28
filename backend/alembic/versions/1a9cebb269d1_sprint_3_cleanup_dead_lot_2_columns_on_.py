"""Sprint 3 cleanup dead Lot 2 columns on entreprise

Revision ID: 1a9cebb269d1
Revises: 381843cf212d
Create Date: 2026-04-28 10:00:42.674647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a9cebb269d1'
down_revision: Union[str, Sequence[str], None] = '381843cf212d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch_alter_table : indispensable pour drop_column sur SQLite,
    # no-op pour Postgres.
    with op.batch_alter_table("entreprise") as batch_op:
        batch_op.drop_column("heures_productives_mensuelles")
        batch_op.drop_column("ratio_encre_m2_couleur")
        batch_op.drop_column("taux_chutes_defaut")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("entreprise") as batch_op:
        batch_op.add_column(
            sa.Column("taux_chutes_defaut", sa.Numeric(precision=5, scale=4), nullable=True)
        )
        batch_op.add_column(
            sa.Column("ratio_encre_m2_couleur", sa.Numeric(precision=8, scale=6), nullable=True)
        )
        batch_op.add_column(
            sa.Column("heures_productives_mensuelles", sa.Integer(), nullable=True)
        )
