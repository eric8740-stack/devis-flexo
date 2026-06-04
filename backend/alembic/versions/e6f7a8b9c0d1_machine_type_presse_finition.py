"""Ajoute `machine.type_machine` (presse/finition) + re-type les finitions.

#4.3 — Le modèle `Machine` n'avait aucun champ de rôle : les lignes de
finition (Daco, Rotoflex) apparaissaient comme des presses dans les candidats
de l'optim. On ajoute `type_machine` ("presse" par défaut) et on re-type les
finitions connues. Le loader d'optim ne chargera que les presses.

Schéma :
  - ADD COLUMN `type_machine` VARCHAR(20) NOT NULL DEFAULT 'presse' → toutes
    les machines EXISTANTES deviennent "presse" (non-régressif).

Données (idempotent, TOUS tenants — validé Eric : une Daco/Rotoflex est une
finition quel que soit le tenant) :
  - UPDATE type_machine='finition' sur les machines dont le nom évoque une
    finition. Match ROBUSTE par motif (case-insensitive via lower()) plutôt
    que par noms exacts, car les noms réels varient :
      * compte démo (seed) : "Daco D250 ligne finition" (table `machine`) ;
      * "Daco D-Series" est une `machine_rebobineuse` (table séparée, NON
        concernée) ;
      * "ROTOFLEX VSI 330" n'existe pas dans le seed mais peut exister en prod.
    Motifs : daco / rotoflex / finition. Aucune presse du parc (Mark Andy P5,
    Atelier 2, Mark Andy 2200, OMET, Nilpeter) ne matche.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "machine",
        sa.Column(
            "type_machine",
            sa.String(length=20),
            nullable=False,
            server_default="presse",
        ),
    )
    # Re-type les finitions (idempotent ; re-run = mêmes valeurs). lower()
    # rend le LIKE insensible à la casse (SQLite ET Postgres).
    op.execute(
        "UPDATE machine SET type_machine = 'finition' "
        "WHERE lower(nom) LIKE '%daco%' "
        "OR lower(nom) LIKE '%rotoflex%' "
        "OR lower(nom) LIKE '%finition%'"
    )


def downgrade() -> None:
    op.drop_column("machine", "type_machine")
