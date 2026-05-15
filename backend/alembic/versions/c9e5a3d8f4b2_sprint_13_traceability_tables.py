"""Sprint 13 — Lot S13.F : tables traçabilité photos + rapports qualité.

Crée les 2 tables fondations de **FlexoCheck** (module IA qualité). Les
workflows API + capture mobile + génération PDF + analyse IA = Sprint
14/15. Ici on matérialise UNIQUEMENT les tables pour que les futurs
sprints n'aient pas à pousser une nouvelle migration en prod sur ce
sujet.

  - rapport_qualite_production : 1 row par run production. Stocke statut,
    archivage PDF (URL + SHA-256), timestamps par étape (impression /
    finition / rebobinage / conditionnement) + durées calculées, mode
    de diffusion, token public, stats agrégées (nb contrôles, écarts
    majeurs/mineurs, score moyen), archivage paramétrable.
    Inclut directement les colonnes du ALTER d'extension CdC (pas de
    2ᵉ migration séparée).

  - photo_production : table générique pour TOUTES les photos d'un run
    (7 type_etape possibles : 1er_tirage, controle_continu, finition,
    bobine_finie, palette_face, palette_dessus, etiquette_palette).
    FK rapport_qualite_id NULLABLE (les photos peuvent exister avant
    rattachement final).

Multi-tenant : entreprise_id NOT NULL FK CASCADE sur les 2 tables.

Ordre de création : rapport AVANT photo (FK).
Ordre de drop : photo AVANT rapport.

Revision ID: c9e5a3d8f4b2
Revises: b8d4e9f7c2a1 (Sprint 13 Lot S13.B business models)
Create Date: 2026-05-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e5a3d8f4b2"
down_revision: Union[str, Sequence[str], None] = "b8d4e9f7c2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- rapport_qualite_production --------------------------------------
    op.create_table(
        "rapport_qualite_production",
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
        # État
        sa.Column("statut", sa.String(20), nullable=True),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column("pdf_genere_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf_hash_sha256", sa.String(64), nullable=True),
        # Timestamps de production (global)
        sa.Column("production_debut_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("production_fin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duree_production_min", sa.Integer(), nullable=True),
        sa.Column("duree_estimee_min", sa.Integer(), nullable=True),
        sa.Column("ecart_temps_estime_pct", sa.Numeric(5, 2), nullable=True),
        # Diffusion
        sa.Column("mode_diffusion", sa.String(30), nullable=True),
        sa.Column(
            "email_client_envoye_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("lien_public_token", sa.String(100), nullable=True),
        sa.Column("lien_public_expire_at", sa.DateTime(timezone=True), nullable=True),
        # Stats agrégées
        sa.Column("nb_controles_total", sa.Integer(), nullable=True),
        sa.Column("nb_ecarts_majeurs", sa.Integer(), nullable=True),
        sa.Column("nb_ecarts_mineurs", sa.Integer(), nullable=True),
        sa.Column("nb_retirages_necessaires", sa.Integer(), nullable=True),
        sa.Column("score_moyen_conformite", sa.Numeric(5, 2), nullable=True),
        sa.Column("validation_finale", sa.String(30), nullable=True),
        # Archivage
        sa.Column(
            "duree_conservation_ans",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column("archive_at", sa.DateTime(timezone=True), nullable=True),
        # Extension : timestamps + durées par étape
        sa.Column("impression_debut_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("impression_fin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finition_debut_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finition_fin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rebobinage_debut_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rebobinage_fin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "conditionnement_debut_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "conditionnement_fin_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("duree_impression_min", sa.Integer(), nullable=True),
        sa.Column("duree_finition_min", sa.Integer(), nullable=True),
        sa.Column("duree_rebobinage_min", sa.Integer(), nullable=True),
        sa.Column("duree_conditionnement_min", sa.Integer(), nullable=True),
        sa.Column("duree_totale_chaine_min", sa.Integer(), nullable=True),
        sa.Column("nb_palettes_total", sa.Integer(), nullable=True),
        sa.Column("nb_palettes_validees", sa.Integer(), nullable=True),
        sa.Column("etape_la_plus_longue", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_rapport_qualite_production_entreprise_id",
        "rapport_qualite_production",
        ["entreprise_id"],
    )
    op.create_index(
        "ix_rapport_qualite_production_devis_id",
        "rapport_qualite_production",
        ["devis_id"],
    )

    # ----- photo_production ------------------------------------------------
    op.create_table(
        "photo_production",
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
        sa.Column(
            "rapport_qualite_id",
            sa.Integer(),
            sa.ForeignKey("rapport_qualite_production.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("type_etape", sa.String(30), nullable=False),
        sa.Column("photo_url", sa.Text(), nullable=False),
        sa.Column("photo_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "operateur_id",
            sa.Integer(),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reference_url", sa.Text(), nullable=True),
        sa.Column("resultats_analyse_ia", sa.JSON(), nullable=True),
        sa.Column("score_conformite", sa.Numeric(5, 2), nullable=True),
        sa.Column("ecarts_detectes", sa.JSON(), nullable=True),
        sa.Column("numero_palette", sa.Integer(), nullable=True),
        sa.Column("nb_bobines_palette", sa.Integer(), nullable=True),
        sa.Column("poids_palette_kg", sa.Numeric(7, 2), nullable=True),
        sa.Column("etiquette_palette_data", sa.JSON(), nullable=True),
        sa.Column("decision_finale", sa.String(30), nullable=True),
        sa.Column("motif_decision", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_photo_production_entreprise_id",
        "photo_production",
        ["entreprise_id"],
    )
    op.create_index(
        "ix_photo_production_devis_id", "photo_production", ["devis_id"]
    )
    op.create_index(
        "ix_photo_production_rapport_qualite_id",
        "photo_production",
        ["rapport_qualite_id"],
    )


def downgrade() -> None:
    # Ordre inverse : photo (qui a la FK vers rapport) AVANT rapport
    op.drop_index(
        "ix_photo_production_rapport_qualite_id", table_name="photo_production"
    )
    op.drop_index("ix_photo_production_devis_id", table_name="photo_production")
    op.drop_index(
        "ix_photo_production_entreprise_id", table_name="photo_production"
    )
    op.drop_table("photo_production")

    op.drop_index(
        "ix_rapport_qualite_production_devis_id",
        table_name="rapport_qualite_production",
    )
    op.drop_index(
        "ix_rapport_qualite_production_entreprise_id",
        table_name="rapport_qualite_production",
    )
    op.drop_table("rapport_qualite_production")
