"""Sprint 13 — Lot S13.B : 6 modèles métier pour le moteur d'optimisation.

Crée les 6 nouvelles tables qui portent l'architecture FlexoCompare v2 :

  - cylindre_magnetique    : catalogue cylindres par développé (19 ICE standards)
  - machine_imprimerie     : parc machines avec vitesse_pratique_m_min réaliste
  - matiere                : catalogue matières (papier/film/thermique/syntétique)
  - option_fabrication     : 20 options (impression/finition/données/sécurité/...)
  - bareme                 : table générique 4 types (échenillage, banane, confort,
                             compensation_laize_dev) avec contenu JSON
  - configuration_pose     : résultats du moteur d'optimisation (UP TO 3 par devis)

Ces tables COEXISTENT avec les tables existantes (machine, complexe, etc.)
sans les remplacer. L'ancien moteur de coûts (V1a/V1b sacrés) reste branché
sur les anciennes tables ; le nouveau moteur d'optimisation Sprint 13
utilisera ces 6 nouvelles. Migration progressive Sprint 14+.

Multi-tenant : toutes les tables ont `entreprise_id` FK CASCADE, sauf
`option_fabrication.entreprise_id` qui est NULLABLE (NULL = catalogue
global livré au seed, NOT NULL = override imprimerie).

Revision ID: b8d4e9f7c2a1
Revises: a5f8c2e1d3b9 (Sprint 13 Lot S13.A user modules)
Create Date: 2026-05-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8d4e9f7c2a1"
down_revision: Union[str, Sequence[str], None] = "a5f8c2e1d3b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- cylindre_magnetique ---------------------------------------------
    op.create_table(
        "cylindre_magnetique",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("developpe_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("machine_repere", sa.String(20), nullable=True),
        sa.Column("nb_pc_10p", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_pc_13p", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_pc_2200", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_pc_p5", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("date_inventaire", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cylindre_magnetique_entreprise_id",
        "cylindre_magnetique",
        ["entreprise_id"],
    )

    # ----- machine_imprimerie ----------------------------------------------
    op.create_table(
        "machine_imprimerie",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("marque", sa.String(50), nullable=True),
        sa.Column("modele", sa.String(50), nullable=True),
        sa.Column("repere_court", sa.String(20), nullable=True),
        sa.Column("laize_totale_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("laize_utile_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("nb_groupes_couleurs", sa.Integer(), nullable=True),
        sa.Column(
            "nb_postes_decoupe", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "vitesse_nominale_constructeur_m_min", sa.Integer(), nullable=True
        ),
        sa.Column("vitesse_pratique_m_min", sa.Integer(), nullable=False),
        sa.Column("vitesse_par_matiere", sa.JSON(), nullable=True),
        sa.Column("vitesse_max_tours_h", sa.Integer(), nullable=True),
        sa.Column("cout_horaire_eur", sa.Numeric(8, 2), nullable=True),
        sa.Column("cylindres_compatibles", sa.JSON(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("type_encre_supportee", sa.JSON(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("date_acquisition", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_machine_imprimerie_entreprise_id",
        "machine_imprimerie",
        ["entreprise_id"],
    )

    # ----- matiere ---------------------------------------------------------
    op.create_table(
        "matiere",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("libelle", sa.String(200), nullable=False),
        sa.Column("categorie", sa.String(50), nullable=True),
        sa.Column("sous_type", sa.String(50), nullable=True),
        sa.Column("grammage_gm2", sa.Integer(), nullable=True),
        sa.Column("epaisseur_microns", sa.Integer(), nullable=True),
        sa.Column("adhesifs_compatibles", sa.JSON(), nullable=True),
        sa.Column(
            "est_transparent", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("opacite_pct", sa.Numeric(4, 1), nullable=True),
        sa.Column("certifications_sanitaires", sa.JSON(), nullable=True),
        sa.Column("certifications_env", sa.JSON(), nullable=True),
        sa.Column("fournisseurs", sa.JSON(), nullable=True),
        sa.Column("notes_techniques", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_matiere_entreprise_id", "matiere", ["entreprise_id"])

    # ----- option_fabrication ----------------------------------------------
    # ⚠️ entreprise_id NULLABLE : NULL = catalogue global livré au seed,
    # NOT NULL = override imprimerie (merge override > global dans le moteur).
    op.create_table(
        "option_fabrication",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("libelle", sa.String(200), nullable=False),
        sa.Column("categorie", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "ajoute_cliches", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "ajoute_couleurs", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "ajoute_outils_decoupe",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "groupes_couleurs_requis",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("modules_speciaux_requis", sa.JSON(), nullable=True),
        sa.Column(
            "est_silhouette_auto",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "ajoute_temps_calage_min",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "coef_vitesse_impact",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column(
            "coef_gache_impact",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column("forfait_eur", sa.Numeric(8, 2), nullable=True),
        sa.Column("prix_au_m2_eur", sa.Numeric(8, 4), nullable=True),
        sa.Column("prix_au_mille_eur", sa.Numeric(8, 2), nullable=True),
        sa.Column("cout_consommable_eur", sa.Numeric(8, 2), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_option_fabrication_entreprise_id",
        "option_fabrication",
        ["entreprise_id"],
    )

    # ----- bareme ----------------------------------------------------------
    op.create_table(
        "bareme",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("nom", sa.String(100), nullable=True),
        sa.Column("applicable_aux_machines", sa.JSON(), nullable=True),
        sa.Column("bareme_data", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_bareme_entreprise_id", "bareme", ["entreprise_id"])

    # ----- configuration_pose ----------------------------------------------
    op.create_table(
        "configuration_pose",
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
            nullable=True,
        ),
        sa.Column(
            "cylindre_id",
            sa.Integer(),
            sa.ForeignKey("cylindre_magnetique.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "machine_id",
            sa.Integer(),
            sa.ForeignKey("machine_imprimerie.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("nb_poses_dev", sa.Integer(), nullable=False),
        sa.Column("nb_poses_laize", sa.Integer(), nullable=False),
        sa.Column("nb_poses_total", sa.Integer(), nullable=False),
        sa.Column("intervalle_dev_reel_mm", sa.Numeric(4, 2), nullable=True),
        sa.Column("intervalle_laize_reel_mm", sa.Numeric(4, 2), nullable=True),
        sa.Column(
            "intervalle_laize_souhaitable_mm", sa.Numeric(4, 2), nullable=True
        ),
        sa.Column(
            "consolidation_atteinte",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("rayon_angles_mm", sa.Numeric(4, 1), nullable=True),
        sa.Column(
            "forme_courbe", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "disposition_poses",
            sa.String(20),
            nullable=False,
            server_default="alignee",
        ),
        sa.Column(
            "coef_confort_rayon",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column(
            "coef_quinconce",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column("largeur_plaque_mm", sa.Numeric(6, 2), nullable=True),
        sa.Column("z_mini_effet_banane", sa.Numeric(6, 2), nullable=True),
        sa.Column("qualite_echenillage", sa.String(20), nullable=True),
        sa.Column(
            "coef_vitesse",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column(
            "coef_gache",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column("couleur_alerte", sa.String(10), nullable=True),
        sa.Column("taux_utilisation_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("gache_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("temps_production_h", sa.Numeric(8, 3), nullable=True),
        sa.Column("cout_machine_eur", sa.Numeric(10, 2), nullable=True),
        sa.Column("cout_matiere_eur", sa.Numeric(10, 2), nullable=True),
        sa.Column("cout_total_eur", sa.Numeric(10, 2), nullable=True),
        sa.Column("surcout_vs_optimal_eur", sa.Numeric(10, 2), nullable=True),
        sa.Column("score", sa.Numeric(8, 2), nullable=True),
        sa.Column("type_config", sa.String(20), nullable=True),
        sa.Column(
            "est_retenue", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "forcage_manuel",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("valeurs_recommandees_initiales", sa.JSON(), nullable=True),
        sa.Column("champs_surcharges", sa.JSON(), nullable=True),
        sa.Column("motif_forcage", sa.Text(), nullable=True),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_configuration_pose_entreprise_id",
        "configuration_pose",
        ["entreprise_id"],
    )
    op.create_index(
        "ix_configuration_pose_devis_id", "configuration_pose", ["devis_id"]
    )


def downgrade() -> None:
    # Ordre inverse de création pour respecter les FK
    op.drop_index(
        "ix_configuration_pose_devis_id", table_name="configuration_pose"
    )
    op.drop_index(
        "ix_configuration_pose_entreprise_id", table_name="configuration_pose"
    )
    op.drop_table("configuration_pose")

    op.drop_index("ix_bareme_entreprise_id", table_name="bareme")
    op.drop_table("bareme")

    op.drop_index(
        "ix_option_fabrication_entreprise_id", table_name="option_fabrication"
    )
    op.drop_table("option_fabrication")

    op.drop_index("ix_matiere_entreprise_id", table_name="matiere")
    op.drop_table("matiere")

    op.drop_index(
        "ix_machine_imprimerie_entreprise_id", table_name="machine_imprimerie"
    )
    op.drop_table("machine_imprimerie")

    op.drop_index(
        "ix_cylindre_magnetique_entreprise_id", table_name="cylindre_magnetique"
    )
    op.drop_table("cylindre_magnetique")
