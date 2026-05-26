"""Sprint 16 Lot A — Module Rebobinage : tables machine_rebobineuse + parametre_mandrin.

2 changements structurels :

1. CREATE TABLE `machine_rebobineuse` — parc rebobineuses (1..N par
   entreprise). Cohérente avec `machine_imprimerie` (singulier, scope
   entreprise_id NOT NULL FK CASCADE, vitesse_pratique_m_min saisie
   manuelle imprimeur).
2. CREATE TABLE `parametre_mandrin` — paramètres mandrins globaux par
   entreprise (1 row par entreprise, UNIQUE entreprise_id). Pilote le
   moteur d'arbitrage Lot B (auto / pre_coupe / decoupe_interne).

L'extension `client` (9 colonnes profil rebobinage) est REPORTÉE — un
ALTER batch_alter_table sur `client` introduit une régression de 18
tests existants (devis modifier, traceability, sprint12 e2e) dont la
cause n'a pas pu être isolée en investigation rapide. Décidé avec Eric
le 2026-05-26 — l'extension client viendra en commit séparé une fois
la pollution diagnostiquée. Le Lot B (moteur rebobinage) ne dépend
pas du profil client persisté à ce stade (le profil sera passé en
runtime au moteur).

Seeds additifs idempotents pour entreprise_id=1 (compte demo Paysant
& Fils Étiquettes) :
  - 1 row `parametre_mandrin` (mode auto, scie_disponible TRUE car ICE
    est un imprimeur installé avec atelier découpe)
  - 2 rows `machine_rebobineuse` (parc demo Daco D-Series + Karlville K200)

Les seeds utilisent `WHERE NOT EXISTS` pour rester idempotents :
  - Re-run de cette migration sur prod : skip car rows déjà créées
  - Application sur preview Postgres vierge : `entreprise(id=1)` est
    garantie présente par le stub d'Issue #35 (p35a1c7d2f9e8) en amont
    de la chaîne, donc l'INSERT effectif crée les rows.

Sacrés invariants : cette migration ne touche PAS :
  - les tables existantes (uniquement CREATE de 2 nouvelles tables)
  - cost_engine / rotation_se / tables tarif_*
  - L'entreprise id=1 ni ses 114+ records seedés (juste 3 INSERTs
    additifs scopés sur cette entreprise)

Revision ID: q1f3a5d7e9c2
Revises: n5g8c7d4e2b9
Create Date: 2026-05-26
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "q1f3a5d7e9c2"
down_revision: Union[str, Sequence[str], None] = "n5g8c7d4e2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEMO_ENTREPRISE_ID = 1

# Seed parametre_mandrin demo — ICE / Paysant & Fils a une scie
# (atelier de découpe). Le mode "auto" laisse le moteur Lot B arbitrer
# au cas par cas.
SEED_PARAMETRE_MANDRIN_DEMO = {
    "scie_disponible": True,
    "delai_livraison_fournisseur_jours": 5,
    "stock_securite_par_modele": {"25": 200, "38": 150, "76": 80, "152": 30},
    "mode_par_defaut": "auto",
}

# Seed machine_rebobineuse demo — 2 rebobineuses typiques d'un parc
# d'imprimeur ICE / Paysant (valeurs réalistes, ajustables via Mon Parc).
SEED_MACHINES_REBOBINEUSES_DEMO = [
    {
        "nom": "Daco D-Series",
        "marque": "Daco",
        "modele": "D250",
        "laize_max_mm": 250.00,
        "diametre_max_mm": 500,
        "mandrins_supportes": [25, 38, 76, 152],
        "vitesse_pratique_m_min": 80,
        "cout_horaire_eur": 45.00,
        "temps_changement_bobine_min": 1.50,
        "options": ["marquage_bobine_inline"],
    },
    {
        "nom": "Karlville K200",
        "marque": "Karlville",
        "modele": "K200-S",
        "laize_max_mm": 200.00,
        "diametre_max_mm": 400,
        "mandrins_supportes": [25, 38, 76],
        "vitesse_pratique_m_min": 100,
        "cout_horaire_eur": 50.00,
        "temps_changement_bobine_min": 1.00,
        "options": [],
    },
]


def upgrade() -> None:
    """Upgrade schema + seeds idempotents."""

    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. CREATE TABLE machine_rebobineuse
    # ------------------------------------------------------------------
    op.create_table(
        "machine_rebobineuse",
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
        sa.Column("laize_max_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("diametre_max_mm", sa.Integer(), nullable=False),
        sa.Column("mandrins_supportes", sa.JSON(), nullable=True),
        sa.Column("vitesse_pratique_m_min", sa.Integer(), nullable=False),
        sa.Column("cout_horaire_eur", sa.Numeric(8, 2), nullable=False),
        sa.Column(
            "temps_changement_bobine_min", sa.Numeric(5, 2), nullable=False
        ),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column(
            "actif",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_machine_rebobineuse_entreprise",
        "machine_rebobineuse",
        ["entreprise_id"],
    )

    # ------------------------------------------------------------------
    # 2. CREATE TABLE parametre_mandrin (UNIQUE entreprise_id = singleton)
    # ------------------------------------------------------------------
    op.create_table(
        "parametre_mandrin",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scie_disponible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "delai_livraison_fournisseur_jours", sa.Integer(), nullable=True
        ),
        sa.Column("stock_securite_par_modele", sa.JSON(), nullable=True),
        sa.Column(
            "mode_par_defaut",
            sa.String(20),
            nullable=False,
            server_default="auto",
        ),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "date_maj",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "entreprise_id", name="uq_parametre_mandrin_entreprise"
        ),
    )
    op.create_index(
        "ix_parametre_mandrin_entreprise",
        "parametre_mandrin",
        ["entreprise_id"],
    )

    # ------------------------------------------------------------------
    # 3. Seeds additifs idempotents pour entreprise_id=1
    # ------------------------------------------------------------------

    # 3.a parametre_mandrin demo (1 row par entreprise, UNIQUE garantit
    # 1 max — le INSERT SELECT WHERE NOT EXISTS rend explicite l'intention
    # et reste compat SQLite+Postgres).
    bind.execute(
        sa.text(
            """
            INSERT INTO parametre_mandrin (
                entreprise_id,
                scie_disponible,
                delai_livraison_fournisseur_jours,
                stock_securite_par_modele,
                mode_par_defaut
            )
            SELECT :eid, :scie, :delai, :stock, :mode
            WHERE NOT EXISTS (
                SELECT 1 FROM parametre_mandrin WHERE entreprise_id = :eid
            )
            """
        ).bindparams(
            eid=DEMO_ENTREPRISE_ID,
            scie=SEED_PARAMETRE_MANDRIN_DEMO["scie_disponible"],
            delai=SEED_PARAMETRE_MANDRIN_DEMO["delai_livraison_fournisseur_jours"],
            stock=json.dumps(SEED_PARAMETRE_MANDRIN_DEMO["stock_securite_par_modele"]),
            mode=SEED_PARAMETRE_MANDRIN_DEMO["mode_par_defaut"],
        )
    )

    # 3.b machine_rebobineuse demo (2 rows pour entreprise_id=1).
    # Idempotence par couple (entreprise_id, nom) — pas de UNIQUE
    # constraint au schéma, donc WHERE NOT EXISTS suffit.
    for row in SEED_MACHINES_REBOBINEUSES_DEMO:
        bind.execute(
            sa.text(
                """
                INSERT INTO machine_rebobineuse (
                    entreprise_id, nom, marque, modele,
                    laize_max_mm, diametre_max_mm, mandrins_supportes,
                    vitesse_pratique_m_min, cout_horaire_eur,
                    temps_changement_bobine_min, options, actif
                )
                SELECT
                    :eid, :nom, :marque, :modele,
                    :laize, :diam, :mandrins,
                    :vit, :cout,
                    :tps, :options, TRUE
                WHERE NOT EXISTS (
                    SELECT 1 FROM machine_rebobineuse
                    WHERE entreprise_id = :eid AND nom = :nom
                )
                """
            ).bindparams(
                eid=DEMO_ENTREPRISE_ID,
                nom=row["nom"],
                marque=row["marque"],
                modele=row["modele"],
                laize=row["laize_max_mm"],
                diam=row["diametre_max_mm"],
                mandrins=json.dumps(row["mandrins_supportes"]),
                vit=row["vitesse_pratique_m_min"],
                cout=row["cout_horaire_eur"],
                tps=row["temps_changement_bobine_min"],
                options=json.dumps(row["options"]),
            )
        )


def downgrade() -> None:
    """Downgrade — DROP des 2 nouvelles tables.

    Les seeds sont supprimés automatiquement par les `drop_table` (cascade
    interne SQL).
    """
    op.drop_index(
        "ix_parametre_mandrin_entreprise", table_name="parametre_mandrin"
    )
    op.drop_table("parametre_mandrin")

    op.drop_index(
        "ix_machine_rebobineuse_entreprise", table_name="machine_rebobineuse"
    )
    op.drop_table("machine_rebobineuse")
