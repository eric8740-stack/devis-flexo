"""B1 — Machine legacy : enrichir avec les champs optim (convergence option B).

Contexte : `Machine` (Sprint 2, lue par cost_engine SACRE -- cylindre_matcher,
poste_5_roulage, poste_7_mo) devient la source unique du parc machines.
`MachineImprimerie` (Sprint 13.B) sera depreciee en B3. Cette migration B1
ajoute a `Machine` les champs consommes par l'optim/loader (Sprint 13.D.7b),
sans toucher les champs SACRES.

SACRED -- NE PAS MODIFIER :
  - laize_max_mm        (cylindre_matcher.py : largeur plaque)
  - vitesse_moyenne_m_h (poste_5_roulage.py, poste_7_mo.py : V1a 1449,09 EUR)
  - duree_calage_h      (poste_7_mo.py : V1a 1449,09 EUR)

Schema additif :
  - ADD laize_utile_mm         Numeric(6,2) nullable
  - ADD nb_postes_decoupe      Integer NOT NULL server_default '1'
  - ADD vitesse_pratique_m_min Integer nullable
  - ADD options                JSON nullable server_default '[]'

Renommage :
  - nb_couleurs -> nb_groupes_couleurs (preserve les valeurs : P5=8, Atelier2=4,
    Daco=NULL). Le nouveau nom est aligne sur `MachineImprimerie.nb_groupes_couleurs`
    pour preparer la convergence B2/B3.

Data migration scope tenant demo (entreprise_id=1) -- valeurs TRANSITOIRES :
  - laize_utile_mm        := laize_max_mm  (pas de marge supplementaire defauts,
                              a affiner via UI B2 si la marge differe).
  - vitesse_pratique_m_min := vitesse_max_m_min  (idem, a affiner B2).
  - nb_postes_decoupe : reste a server_default 1.
  - options : reste a server_default [].

Les autres tenants (s'il en existe) recoivent les server_default neutres ;
laize_utile_mm + vitesse_pratique_m_min restent NULL chez eux jusqu'a
peuplement explicite via l'UI B2.

Reversible :
  - drop_column x4
  - rename inverse nb_groupes_couleurs -> nb_couleurs

Sur SQLite (dev/tests), batch_alter_table recree la table entiere (le rename
de colonne n'est pas supporte directement en SQLite < 3.25). Sur Postgres
(prod), batch_alter_table compile en ALTER TABLE natif.

Revision ID: z0p4n6r8s1t3
Revises: y9n2i3g7d5f0
Create Date: 2026-05-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


revision: str = "z0p4n6r8s1t3"
down_revision: Union[str, Sequence[str], None] = "y9n2i3g7d5f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema : 4 colonnes additives + 1 rename dans un seul batch
    # (1 seule recreation de table cote SQLite).
    with op.batch_alter_table("machine", schema=None) as batch:
        batch.add_column(
            sa.Column(
                "laize_utile_mm",
                sa.Numeric(6, 2),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "nb_postes_decoupe",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch.add_column(
            sa.Column(
                "vitesse_pratique_m_min",
                sa.Integer(),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "options",
                sa.JSON(),
                nullable=True,
                server_default="[]",
            )
        )
        # Renommage : preserve la donnee (P5=8, Atelier2=4, Daco=NULL).
        batch.alter_column(
            "nb_couleurs",
            new_column_name="nb_groupes_couleurs",
            existing_type=sa.Integer(),
            existing_nullable=True,
        )

    # Data migration scope tenant demo : derive laize_utile_mm et
    # vitesse_pratique_m_min depuis les valeurs existantes (transitoires).
    op.execute(
        text(
            "UPDATE machine "
            "SET laize_utile_mm = laize_max_mm, "
            "    vitesse_pratique_m_min = vitesse_max_m_min "
            "WHERE entreprise_id = 1"
        )
    )


def downgrade() -> None:
    # Sens inverse : rename + drop des 4 colonnes ajoutees.
    # Sur SQLite, l'UPDATE de la data migration n'est pas annule (les valeurs
    # restent dans nb_groupes_couleurs apres rename inverse, ce qui est OK
    # car c'est la donnee historique de nb_couleurs).
    with op.batch_alter_table("machine", schema=None) as batch:
        batch.alter_column(
            "nb_groupes_couleurs",
            new_column_name="nb_couleurs",
            existing_type=sa.Integer(),
            existing_nullable=True,
        )
        batch.drop_column("options")
        batch.drop_column("vitesse_pratique_m_min")
        batch.drop_column("nb_postes_decoupe")
        batch.drop_column("laize_utile_mm")
