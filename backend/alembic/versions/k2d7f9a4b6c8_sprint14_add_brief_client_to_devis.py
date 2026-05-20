"""Sprint 14 Lot 1 — ajout brief client unifié sur devis.

Cinq champs caractérisent la livraison finale au client (commune à tous
les lots d'un devis multi-lots) :

| Champ | Type | Nullable | Default | Commentaire |
|---|---|---|---|---|
| nb_etiquettes_par_rouleau | Integer | True | NULL | Quantité par bobine livrée |
| diametre_max_bobine_mm | Integer | True | NULL | Contrainte machine cliente |
| nb_fronts_sortie | Integer | True | 1 | Nb pistes en sortie |
| type_entree_fichier | Enum | False | 'a_designer' | vierge / bat_pro_fourni / a_designer |
| conditions_stockage | JSONB | True | NULL | {humidite_pct, t_min_c, t_max_c, lieu} |

Tous rétro-compatibles (nullable ou server_default) pour ne pas casser
les devis existants. `type_entree_fichier` est NOT NULL mais doté d'un
server_default → les anciennes lignes prennent 'a_designer' au upgrade,
ce qui est le cas le plus large (cf. brief Sprint 14 §6).

Pattern enum SQL natif aligné sur `devis_statut_enum` (Sprint 4 Lot 4a).
Pattern JSONB+JSON variant aligné sur `lot_production.payload_visuel`
(Brief #33).

Revision ID: k2d7f9a4b6c8
Revises: j1c6e8a3d9b5
Create Date: 2026-05-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k2d7f9a4b6c8"
down_revision: Union[str, Sequence[str], None] = "j1c6e8a3d9b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nom de l'enum SQL — référencé en upgrade ET downgrade pour le drop type
# Postgres (sur SQLite l'enum est un simple CHECK constraint inline, géré
# automatiquement par batch_alter_table).
ENUM_NAME = "devis_type_entree_fichier_enum"
ENUM_VALUES = ("vierge", "bat_pro_fourni", "a_designer")


def upgrade() -> None:
    # Création explicite du type enum Postgres avant l'ALTER TABLE pour que
    # le batch_alter_table SQLite ne tente pas de le créer (il l'inline en
    # CHECK constraint). create_type=False côté column pour éviter le double.
    enum_type = postgresql.ENUM(*ENUM_VALUES, name=ENUM_NAME, create_type=False)
    enum_type.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("devis") as batch_op:
        batch_op.add_column(
            sa.Column("nb_etiquettes_par_rouleau", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("diametre_max_bobine_mm", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "nb_fronts_sortie",
                sa.Integer(),
                nullable=True,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "type_entree_fichier",
                sa.Enum(*ENUM_VALUES, name=ENUM_NAME, create_type=False),
                nullable=False,
                server_default="a_designer",
            )
        )
        batch_op.add_column(
            sa.Column(
                "conditions_stockage",
                postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("devis") as batch_op:
        batch_op.drop_column("conditions_stockage")
        batch_op.drop_column("type_entree_fichier")
        batch_op.drop_column("nb_fronts_sortie")
        batch_op.drop_column("diametre_max_bobine_mm")
        batch_op.drop_column("nb_etiquettes_par_rouleau")

    # Drop du type enum Postgres après que la colonne qui l'utilise est
    # partie (sur SQLite c'était inline, rien à faire).
    enum_type = postgresql.ENUM(*ENUM_VALUES, name=ENUM_NAME, create_type=False)
    enum_type.drop(op.get_bind(), checkfirst=True)
