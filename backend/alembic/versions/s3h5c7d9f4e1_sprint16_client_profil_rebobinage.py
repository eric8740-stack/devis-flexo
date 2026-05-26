"""Sprint 16 — profil rebobinage client (9 colonnes additives).

**Nouvelle approche** (vs WIP avorté `r2g4b6e8c1f3`) : utilisation de
`op.add_column()` au lieu de `op.batch_alter_table()`. SQLite ≥ 3.x
supporte nativement `ALTER TABLE ADD COLUMN`, ce qui évite le
DROP+COPY+RENAME de table et donc le toggle `PRAGMA foreign_keys=OFF/ON`
fragile qui fuyait dans la connexion-pool SQLAlchemy après commit
(cause des 18 régressions observées au Lot A initial).

Pas de toggle PRAGMA → pas de fuite dans le pool → cascade FK reste
ON pour les sessions pytest suivantes → DELETE Devis cascade vers
lot_production normalement → POST /api/devis suivant ne plante plus
en UNIQUE violation.

Le fix racine du leak PRAGMA (event listener `connect` vs `checkout`
sur le pool SQLAlchemy) est un sujet séparé, hors scope.

9 colonnes ajoutées à `client` :

| Colonne | Type | Nullable | Default |
|---|---|---|---|
| diametre_mandrin_mm | Integer | True | NULL |
| diametre_max_bobine_mm | Integer | True | NULL |
| sens_enroulement | Integer | True | NULL |
| nb_etiq_par_bobine_fixe | Integer | True | NULL |
| marquage_bobine_requis | Boolean | False | sa.false() |
| marquage_bobine_format | String(100) | True | NULL |
| mandrin_fourni_par_client | Boolean | False | sa.false() |
| film_protection_requis | Boolean | False | sa.false() |
| conditionnement_souhaite | String(100) | True | NULL |

Idempotence prod : les ~20 clients seedés (entreprise_id=1) reçoivent
les `server_default sa.false()` sur les 3 Boolean (donc valeur `false`
= 0 SQLite, `false` Postgres). Les 6 colonnes nullable restent à NULL
sur les rows existantes — comportement attendu pour des champs profil
qu'on remplira au cas par cas via la fiche client (UI à venir).

**SQLite ADD COLUMN NOT NULL avec DEFAULT** : SQLite accepte ADD COLUMN
NOT NULL **uniquement si un DEFAULT est fourni** (pour remplir les rows
existantes au moment du ALTER). Nos 3 Boolean ont `server_default
=sa.false()` → OK.

Revision ID: s3h5c7d9f4e1
Revises: q1f3a5d7e9c2
Create Date: 2026-05-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "s3h5c7d9f4e1"
down_revision: Union[str, Sequence[str], None] = "q1f3a5d7e9c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajoute les 9 colonnes profil rebobinage à `client`.

    Utilise `op.add_column()` (et non `batch_alter_table`) pour générer
    un `ALTER TABLE ... ADD COLUMN` SQLite natif. Pas de toggle PRAGMA
    nécessaire — pas de DROP/CREATE de table donc aucun risque sur les
    FK incoming (devis.client_id SET NULL).
    """
    # 4 Integer nullable
    op.add_column(
        "client", sa.Column("diametre_mandrin_mm", sa.Integer(), nullable=True)
    )
    op.add_column(
        "client",
        sa.Column("diametre_max_bobine_mm", sa.Integer(), nullable=True),
    )
    op.add_column(
        "client", sa.Column("sens_enroulement", sa.Integer(), nullable=True)
    )
    op.add_column(
        "client",
        sa.Column("nb_etiq_par_bobine_fixe", sa.Integer(), nullable=True),
    )

    # 3 Boolean NOT NULL avec server_default false
    op.add_column(
        "client",
        sa.Column(
            "marquage_bobine_requis",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "client",
        sa.Column(
            "mandrin_fourni_par_client",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "client",
        sa.Column(
            "film_protection_requis",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # 2 String nullable
    op.add_column(
        "client",
        sa.Column("marquage_bobine_format", sa.String(100), nullable=True),
    )
    op.add_column(
        "client",
        sa.Column("conditionnement_souhaite", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    """Drop les 9 colonnes en ordre inverse.

    SQLite ≥ 3.35 (Python 3.13 embarque ~3.45) supporte nativement
    `ALTER TABLE DROP COLUMN`. Postgres natif aussi. Pas besoin de
    batch_alter_table.
    """
    op.drop_column("client", "conditionnement_souhaite")
    op.drop_column("client", "marquage_bobine_format")
    op.drop_column("client", "film_protection_requis")
    op.drop_column("client", "mandrin_fourni_par_client")
    op.drop_column("client", "marquage_bobine_requis")
    op.drop_column("client", "nb_etiq_par_bobine_fixe")
    op.drop_column("client", "sens_enroulement")
    op.drop_column("client", "diametre_max_bobine_mm")
    op.drop_column("client", "diametre_mandrin_mm")
