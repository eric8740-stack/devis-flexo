"""Ajoute `epaisseur_paroi_mm` (nullable) sur `parametre_mandrin`.

Bug #6 (chaîne Format → Outil → Matière → Bobinage) — étape 6.1 : on crée
le champ `epaisseur_paroi_mm` (épaisseur de paroi du mandrin, en mm) qui
servira au calcul du Ø rouleau (étape 6.2, NON câblé ici).

Additive et réversible. Colonne NULLABLE sans server_default : `NULL = inconnu`
(aucune valeur de paroi en dur ; l'imprimeur renseignera ensuite). Aucune ligne
existante n'est modifiée. Pas de DDL au-delà de l'ajout de colonne.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "parametre_mandrin",
        sa.Column("epaisseur_paroi_mm", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parametre_mandrin", "epaisseur_paroi_mm")
