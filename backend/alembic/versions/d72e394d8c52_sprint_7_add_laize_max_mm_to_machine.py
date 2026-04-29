"""Sprint 7 add laize_max_mm to machine

Revision ID: d72e394d8c52
Revises: addf7c687f84
Create Date: 2026-04-29 12:37:20.270368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd72e394d8c52'
down_revision: Union[str, Sequence[str], None] = 'addf7c687f84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    server_default=260 utilisé uniquement pour passer la contrainte NOT NULL
    sur les lignes existantes (3 machines en local + 3 en prod). Le seed CSV
    machine.csv applique ensuite les vraies valeurs (330 / 250 / 260).
    Default DB pas droppé après pour rester safe lors d'une recréation
    accidentelle de ligne sans laize.
    """
    op.add_column(
        'machine',
        sa.Column(
            'laize_max_mm',
            sa.Numeric(precision=6, scale=2),
            nullable=False,
            server_default=sa.text('260'),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('machine', 'laize_max_mm')
