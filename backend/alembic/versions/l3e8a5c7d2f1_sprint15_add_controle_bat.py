"""Sprint 15 Lot 1 — ajout table controle_bat (FlexoCheck).

Une row par tentative de contrôle BAT IA. Chaînage des re-tirages via
self-FK `controle_bat_precedent_id` (SET NULL pour préserver l'historique
si une row parente disparaît).

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
devis_id NOT NULL FK CASCADE.

JSONB pour les colonnes `resultats_comparaison` et `ecarts_detectes` —
variant JSON sur SQLite (pattern Brief #33 / Sprint 14).

Aucune table existante touchée. La table est créée from scratch, donc
applicable sans risque sur prod (entreprise id=1 déjà présente, mais
inutile ici : pas de backfill, pas de FK ajoutée à une table peuplée).

Revision ID: l3e8a5c7d2f1
Revises: k2d7f9a4b6c8
Create Date: 2026-05-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "l3e8a5c7d2f1"
down_revision: Union[str, Sequence[str], None] = "k2d7f9a4b6c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "controle_bat",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "devis_id",
            sa.Integer(),
            sa.ForeignKey("devis.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # BAT de référence
        sa.Column("bat_url", sa.Text(), nullable=False),
        sa.Column(
            "bat_date_validation", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("bat_valide_par", sa.String(200), nullable=True),
        # Photo 1er tirage
        sa.Column("premier_tirage_url", sa.Text(), nullable=False),
        sa.Column(
            "premier_tirage_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # Résultats IA
        sa.Column(
            "resultats_comparaison",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("score_conformite", sa.Numeric(5, 2), nullable=True),
        sa.Column("decision_recommandee", sa.String(30), nullable=True),
        sa.Column(
            "ecarts_detectes",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "nb_ecarts_majeurs",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "nb_ecarts_mineurs",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("niveau_confiance", sa.String(20), nullable=True),
        # Décision opérateur
        sa.Column("decision_finale", sa.String(30), nullable=False),
        sa.Column("decideur", sa.String(200), nullable=False),
        sa.Column("motif_decision", sa.Text(), nullable=True),
        # Chaînage re-tirage
        sa.Column(
            "tentative_numero",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "controle_bat_precedent_id",
            sa.Integer(),
            sa.ForeignKey("controle_bat.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Coût API
        sa.Column("cout_api_eur", sa.Numeric(6, 4), nullable=True),
        # Sens sortie (Lot 4)
        sa.Column("sens_sortie_detecte", sa.String(3), nullable=True),
        sa.Column("sens_enroulement_demande", sa.String(3), nullable=True),
        sa.Column("coherence_sens", sa.Boolean(), nullable=True),
        sa.Column("action_correction_sens", sa.String(50), nullable=True),
        sa.Column("position_operateur_conforme", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_controle_bat_entreprise", "controle_bat", ["entreprise_id"]
    )
    op.create_index("ix_controle_bat_devis", "controle_bat", ["devis_id"])
    op.create_index(
        "ix_controle_bat_precedent",
        "controle_bat",
        ["controle_bat_precedent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_controle_bat_precedent", table_name="controle_bat")
    op.drop_index("ix_controle_bat_devis", table_name="controle_bat")
    op.drop_index("ix_controle_bat_entreprise", table_name="controle_bat")
    op.drop_table("controle_bat")
