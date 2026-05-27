"""Brief stratégique v2 Phase 1 — socle : tables config par entreprise.

Crée 3 tables de configuration scopées entreprise_id (onglet Stratégique) :
  - config_couts        (singleton/tenant) : coûts variables/fixes + marges
  - config_changements  (singleton/tenant) : durées + coûts changements
  - config_roulage      (collection/tenant) : débits par format

Additive, réversible. Prépare la sortie des données ICE hardcodées vers une
config par tenant (le moteur les consommera en Phase 2). Aucune donnée
existante touchée ; le seed template remplit les valeurs neutres par défaut.

Revision ID: w7l9g1e5d3f8
Revises: v6k8f0d4c2e7
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "w7l9g1e5d3f8"
down_revision: Union[str, Sequence[str], None] = "v6k8f0d4c2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "config_couts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entreprise_id", sa.Integer(), nullable=False),
        sa.Column("cout_exploitation_machine_eur_h", sa.Numeric(10, 2), nullable=False),
        sa.Column("cout_operateur_eur_h", sa.Numeric(10, 2), nullable=False),
        sa.Column("cout_energies_eur_h", sa.Numeric(10, 2), nullable=False),
        sa.Column("cout_fixe_atelier_eur_mois", sa.Numeric(10, 2), nullable=False),
        sa.Column("cout_fixe_maintenance_eur_mois", sa.Numeric(10, 2), nullable=False),
        sa.Column("marge_standard_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("buffer_rebut_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("buffer_setup_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "date_maj",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["entreprise_id"], ["entreprise.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entreprise_id", name="uq_config_couts_entreprise"),
    )
    op.create_index(
        "ix_config_couts_entreprise_id", "config_couts", ["entreprise_id"]
    )

    op.create_table(
        "config_changements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entreprise_id", sa.Integer(), nullable=False),
        sa.Column("changement_couleur_duree_min", sa.Integer(), nullable=False),
        sa.Column("changement_couleur_cout_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("changement_format_duree_min", sa.Integer(), nullable=False),
        sa.Column("changement_format_cout_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("nettoyage_duree_min", sa.Integer(), nullable=False),
        sa.Column("nettoyage_cout_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "date_maj",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["entreprise_id"], ["entreprise.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entreprise_id", name="uq_config_changements_entreprise"
        ),
    )
    op.create_index(
        "ix_config_changements_entreprise_id",
        "config_changements",
        ["entreprise_id"],
    )

    op.create_table(
        "config_roulage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entreprise_id", sa.Integer(), nullable=False),
        sa.Column("format_libelle", sa.String(50), nullable=False),
        sa.Column("debit_mm_s", sa.Integer(), nullable=False),
        sa.Column("mode_roulage", sa.String(20), nullable=False),
        sa.Column("rebut_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "date_maj",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["entreprise_id"], ["entreprise.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_config_roulage_entreprise_id", "config_roulage", ["entreprise_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_config_roulage_entreprise_id", table_name="config_roulage")
    op.drop_table("config_roulage")
    op.drop_index(
        "ix_config_changements_entreprise_id", table_name="config_changements"
    )
    op.drop_table("config_changements")
    op.drop_index("ix_config_couts_entreprise_id", table_name="config_couts")
    op.drop_table("config_couts")
