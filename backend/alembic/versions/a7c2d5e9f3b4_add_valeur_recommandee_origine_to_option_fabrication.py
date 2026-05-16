"""Ajout colonne valeur_recommandee_origine sur option_fabrication.

Sert à conserver, au moment où le tenant active une option depuis le
catalogue master (POST /api/parametres/options-fabrication/from-master/{code}),
un snapshot JSON des coefs et tarifs "recommandés" Sprint 13. La page
d'édition affiche ce snapshot en hint ("recommandé : X.XX") pour aider
le pilote à comprendre l'écart avec ses propres valeurs.

Revision ID: a7c2d5e9f3b4
Revises: f6b3c8e4d712
Create Date: 2026-05-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7c2d5e9f3b4"
down_revision: Union[str, Sequence[str], None] = "f6b3c8e4d712"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("option_fabrication") as batch_op:
        batch_op.add_column(
            sa.Column("valeur_recommandee_origine", sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("option_fabrication") as batch_op:
        batch_op.drop_column("valeur_recommandee_origine")
