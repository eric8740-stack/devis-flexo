"""Lot F — paramètres bobinage / appro matière (géométrie seule, AUCUN coût).

Ajoute les 3 paramètres pilotant le bloc « bobinage » de /preview (affichage
appro + géométrie bobine), sans toucher au cost_engine :

  - entreprise.ml_par_bobine_defaut          Integer NOT NULL server_default '2000'
  - machine.diametre_max_bobine_mm           Integer NOT NULL server_default '1100'
  - machine.temps_changement_bobine_min      Integer NOT NULL server_default '15'

Tous additifs, avec server_default → les lignes existantes (tous tenants)
reçoivent les défauts métier neutres. Aucune donnée touchée ailleurs ; les
sacrés (V1a 1 424,31 / P0b 695,36) sont hors périmètre (rien de chiffré).

Le temps de changement est AFFICHÉ (temps d'arrêt indicatif), JAMAIS facturé :
la facturation du temps d'arrêt est un lot dédié ultérieur (touchera le
cost_engine → re-baseline contrôlée).

Reversible : drop_column des 3 colonnes.

DDL natif (op.add_column / op.drop_column) — PAS batch_alter_table : `machine`
est une table PARENT (FK depuis devis / lot_production / porte_cliche) et la
recréation de table SQLite par batch, avec PRAGMA foreign_keys=ON forcé (cf.
app/db.py), vide les lignes de la table parente. SQLite ≥ 3.35 (bundlé Python
3.13) + Postgres supportent ADD/DROP COLUMN natifs in-place → données
préservées. Même pattern FK-safe que la migration `a2b4c6d8e0f1`.

Revision ID: c4d6e8f0a1b3
Revises: b3c5d7e9f1a2
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4d6e8f0a1b3"
down_revision: Union[str, Sequence[str], None] = "b3c5d7e9f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "entreprise",
        sa.Column(
            "ml_par_bobine_defaut",
            sa.Integer(),
            nullable=False,
            server_default="2000",
        ),
    )
    op.add_column(
        "machine",
        sa.Column(
            "diametre_max_bobine_mm",
            sa.Integer(),
            nullable=False,
            server_default="1100",
        ),
    )
    op.add_column(
        "machine",
        sa.Column(
            "temps_changement_bobine_min",
            sa.Integer(),
            nullable=False,
            server_default="15",
        ),
    )


def downgrade() -> None:
    op.drop_column("machine", "temps_changement_bobine_min")
    op.drop_column("machine", "diametre_max_bobine_mm")
    op.drop_column("entreprise", "ml_par_bobine_defaut")
