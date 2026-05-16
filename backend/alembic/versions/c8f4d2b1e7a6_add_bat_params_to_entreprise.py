"""Ajout 4 paramètres BAT (Bon À Tirer) sur la table entreprise.

PR #9.1 (FlexoCompare BAT MVP) : ces 4 paramètres tenant pilotent les
calculs d'implantation (laize papier, chute latérale, refilage,
laize liner) affichés sur le schéma BAT de la page /optimisation.

Colonnes ajoutées (toutes NOT NULL avec defaults métier ICE) :
  - chute_laterale_min_mm   DECIMAL(5,2) default 10.00
        Marge de chute mini de chaque côté de la plaque pour
        l'échenillage (anti-décollement bords).
  - palier_laize_papier_mm  INTEGER default 10
        Arrondi de la laize matière commandée (les fournisseurs
        livrent par palier standard, typiquement 10 mm).
  - refilage_systematique   BOOLEAN default FALSE
        Si TRUE, refilage à imposer systématiquement (option
        finition par défaut). Surchargeable au devis (en 9.2+).
  - marge_liner_mm          DECIMAL(5,2) default 2.50
        Marge supplémentaire de chaque côté de l'étiquette pour
        le liner siliconé chez le client (vue bobine fille).

Revision ID: c8f4d2b1e7a6
Revises: b4e9c7a1f3d2
Create Date: 2026-05-16
"""
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c8f4d2b1e7a6"
down_revision: Union[str, Sequence[str], None] = "b4e9c7a1f3d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("entreprise") as batch_op:
        batch_op.add_column(
            sa.Column(
                "chute_laterale_min_mm",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="10.00",
            )
        )
        batch_op.add_column(
            sa.Column(
                "palier_laize_papier_mm",
                sa.Integer(),
                nullable=False,
                server_default="10",
            )
        )
        batch_op.add_column(
            sa.Column(
                "refilage_systematique",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "marge_liner_mm",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="2.50",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("entreprise") as batch_op:
        batch_op.drop_column("marge_liner_mm")
        batch_op.drop_column("refilage_systematique")
        batch_op.drop_column("palier_laize_papier_mm")
        batch_op.drop_column("chute_laterale_min_mm")
