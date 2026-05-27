"""Lot 1 complexe enrichi — schéma : champs optim + certifs + grammage Numeric.

Prépare le pont matière↔complexe en alignant la table `complexe`
(cost_engine, Sprint 2) sur les caractéristiques que le moteur
d'optimisation lit déjà sur la table `matiere` (Sprint 13).

Changements de schéma :
  - grammage_g_m2 : Integer → Numeric(5,1). Les films ont un grammage de
    FACE non entier (épaisseur × densité, ex. BOPP 50µ × 0.91 = 45.5 g/m²).
    Neutre pour le cost_engine Poste 1 : le grammage s'annule algébriquement
    (cout = surface × prix_m2, cf. poste_1_matiere._resolve_prix_kg) — le
    benchmark figé (complexe id=31, grammage 80 → 80.0) reste identique.
  - epaisseur_microns   : Integer  nullable (films ; NULL pour les papiers)
  - est_transparent     : Boolean  NOT NULL default False
  - opacite_pct         : Numeric(4,1) nullable
  - sous_type           : String(50)   nullable
  - certifications_sanitaires : JSON   nullable
  - certifications_env        : JSON   nullable

Le remplissage des 31 complexes existants (entreprise_id=1) est une
migration de DONNÉES séparée (Lot 1 commit 2).

SQLite : batch_alter_table (recreate). PostgreSQL : ALTER natif. Toggle
PRAGMA foreign_keys par sécurité pendant le recreate (FK sortante
fournisseur_id préservée).

Revision ID: u5j7e9c3b1d6
Revises: t4i6d8b2a9c5
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "u5j7e9c3b1d6"
down_revision: Union[str, Sequence[str], None] = "t4i6d8b2a9c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("complexe") as batch_op:
        batch_op.alter_column(
            "grammage_g_m2",
            existing_type=sa.Integer(),
            type_=sa.Numeric(5, 1),
            existing_nullable=True,
        )
        batch_op.add_column(sa.Column("epaisseur_microns", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "est_transparent",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("opacite_pct", sa.Numeric(4, 1), nullable=True))
        batch_op.add_column(sa.Column("sous_type", sa.String(50), nullable=True))
        batch_op.add_column(
            sa.Column("certifications_sanitaires", sa.JSON(), nullable=True)
        )
        batch_op.add_column(sa.Column("certifications_env", sa.JSON(), nullable=True))

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("complexe") as batch_op:
        batch_op.drop_column("certifications_env")
        batch_op.drop_column("certifications_sanitaires")
        batch_op.drop_column("sous_type")
        batch_op.drop_column("opacite_pct")
        batch_op.drop_column("est_transparent")
        batch_op.drop_column("epaisseur_microns")
        batch_op.alter_column(
            "grammage_g_m2",
            existing_type=sa.Numeric(5, 1),
            type_=sa.Integer(),
            existing_nullable=True,
        )

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=ON")
