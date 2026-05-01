"""Sprint 9 v2 — extend tarif_poste + refactor statut to actif

Revision ID: 5a1e9b20c4f8
Revises: b89d835f3823
Create Date: 2026-05-02 09:00:00.000000

Trois opérations atomiques pour Sprint 9 v2 Lot 9a :

1. tarif_poste : ajout colonnes `description` (Text NULL) + `ordre_affichage`
   (Integer NOT NULL DEFAULT 0). Seed les 7 lignes existantes avec leurs
   description/ordre, puis INSERT 3 nouvelles lignes (Dette 1 :
   outil_base_eur, outil_par_trace_eur, surcout_forme_speciale_pct).

2. machine : refactor `statut` String → `actif` Boolean.
   Mapping : 'actif'/'maintenance' → True (perte info maintenance assumée
   par Eric brief 4.3), 'inactif' → False.

3. complexe : refactor `statut` String ('actif'/'archive') → `actif` Boolean.
   Mapping : 'actif' → True, 'archive' → False.

4. partenaire_st : refactor `statut` String ('actif'/'inactif') → `actif`
   Boolean. Mapping : 'actif' → True, 'inactif' → False.

Utilise `op.batch_alter_table` pour compatibilité SQLite (dev) et
PostgreSQL (prod Railway). UPDATEs DB-agnostic via TRUE/FALSE supportés
par les deux moteurs (SQLite ≥ 3.23, PostgreSQL natif).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5a1e9b20c4f8"
down_revision: Union[str, Sequence[str], None] = "b89d835f3823"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Descriptions + ordre_affichage des 7 clés tarif_poste préexistantes.
# Cohérent avec seeds/tarif_poste.csv pour idempotence dev fresh DB.
_TARIF_POSTE_SEEDS_EXISTANTS = [
    (
        "matiere_prix_kg_defaut",
        "Valeur utilisée si le complexe choisi n'a pas de prix matière défini",
        1,
    ),
    (
        "cliche_prix_couleur",
        "Coût d'un cliché par couleur (P3a). Multiplié par nb_couleurs_total",
        1,
    ),
    (
        "calage_forfait",
        "Forfait de mise en route et calage (P4) appliqué une fois par devis",
        1,
    ),
    (
        "roulage_prix_horaire",
        "Prix horaire machine pour le roulage (P5). Multiplié par durée roulage",
        1,
    ),
    (
        "marge_confort_roulage_mm",
        "Marge ajoutée à la laize utile pour le calcul de la surface support (P1)",
        2,
    ),
    (
        "finitions_prix_m2",
        "Prix au m² des opérations de finition standard (P6)",
        1,
    ),
    (
        "mo_prix_horaire",
        "Prix horaire main d'œuvre opérateur (P7) pour calage et roulage",
        1,
    ),
]

# 3 nouvelles lignes outillage (Dette 1 - migration depuis poste_3_cliches.py).
# Valeurs EXACTEMENT identiques aux constantes en dur précédentes pour
# préserver V1a/V1b/V1b forme spé EXACT après refactor moteur (Lot 9b).
_TARIF_POSTE_SEEDS_NOUVEAUX = [
    {
        "cle": "outil_base_eur",
        "poste_numero": 3,
        "libelle": "Coût outil neuf (forfait fixe)",
        "valeur_defaut": 200.0,
        "valeur_min": 100.0,
        "valeur_max": 500.0,
        "unite": "€",
        "actif": True,
        "description": "Forfait fabrication d'un nouvel outil de découpe (P3b mode nouvel outil)",
        "ordre_affichage": 10,
    },
    {
        "cle": "outil_par_trace_eur",
        "poste_numero": 3,
        "libelle": "Coût par trace de complexité",
        "valeur_defaut": 50.0,
        "valeur_min": 20.0,
        "valeur_max": 150.0,
        "unite": "€",
        "actif": True,
        "description": "Coût additionnel par trace de complexité de l'outil neuf (P3b)",
        "ordre_affichage": 11,
    },
    {
        "cle": "surcout_forme_speciale_pct",
        "poste_numero": 3,
        "libelle": "Majoration forme spéciale",
        "valeur_defaut": 1.4,
        "valeur_min": 1.0,
        "valeur_max": 2.0,
        "unite": "×",
        "actif": True,
        "description": "Multiplicateur appliqué au coût outil neuf si forme spéciale (P3b)",
        "ordre_affichage": 12,
    },
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # ------------------------------------------------------------
    # 1. tarif_poste : add description + ordre_affichage
    # ------------------------------------------------------------
    with op.batch_alter_table("tarif_poste") as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "ordre_affichage",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    # Seed des descriptions + ordre des 7 lignes préexistantes
    for cle, desc, ordre in _TARIF_POSTE_SEEDS_EXISTANTS:
        bind.execute(
            sa.text(
                "UPDATE tarif_poste SET description = :desc, ordre_affichage = :ordre "
                "WHERE cle = :cle"
            ),
            {"desc": desc, "ordre": ordre, "cle": cle},
        )

    # INSERT 3 nouvelles lignes outillage (Dette 1)
    for row in _TARIF_POSTE_SEEDS_NOUVEAUX:
        bind.execute(
            sa.text(
                "INSERT INTO tarif_poste "
                "(cle, poste_numero, libelle, valeur_defaut, valeur_min, valeur_max, "
                " unite, actif, description, ordre_affichage) "
                "VALUES (:cle, :poste_numero, :libelle, :valeur_defaut, :valeur_min, "
                " :valeur_max, :unite, :actif, :description, :ordre_affichage)"
            ),
            row,
        )

    # ------------------------------------------------------------
    # 2/3/4. statut → actif sur machine, complexe, partenaire_st
    # ------------------------------------------------------------
    # Mapping métier (validé Eric brief 4.3) :
    # - machine    : 'actif' OR 'maintenance' → True ; 'inactif' → False
    # - complexe   : 'actif' → True ; 'archive' → False
    # - partenaire_st : 'actif' → True ; 'inactif' → False
    refactor_specs = [
        ("machine", "statut IN ('actif', 'maintenance')", "statut = 'inactif'"),
        ("complexe", "statut = 'actif'", "statut = 'archive'"),
        ("partenaire_st", "statut = 'actif'", "statut = 'inactif'"),
    ]
    for table_name, where_true, where_false in refactor_specs:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "actif",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )
        bind.execute(
            sa.text(f"UPDATE {table_name} SET actif = TRUE WHERE {where_true}")
        )
        bind.execute(
            sa.text(f"UPDATE {table_name} SET actif = FALSE WHERE {where_false}")
        )
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("statut")


def downgrade() -> None:
    """Downgrade schema (roundtrip — perte info 'maintenance' acceptée).

    Réinjecte la colonne `statut` String NOT NULL DEFAULT 'actif' avec
    mapping inverse :
    - actif=True  → 'actif'
    - actif=False → 'inactif' (machine, partenaire_st) ou 'archive' (complexe)
    """
    bind = op.get_bind()

    revert_specs = [
        ("machine", "actif", "inactif"),
        ("complexe", "actif", "archive"),
        ("partenaire_st", "actif", "inactif"),
    ]
    for table_name, true_state, false_state in revert_specs:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "statut",
                    sa.String(20),
                    nullable=False,
                    server_default="actif",
                )
            )
        bind.execute(
            sa.text(f"UPDATE {table_name} SET statut = :s WHERE actif = TRUE"),
            {"s": true_state},
        )
        bind.execute(
            sa.text(f"UPDATE {table_name} SET statut = :s WHERE actif = FALSE"),
            {"s": false_state},
        )
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("actif")

    # Drop les 3 lignes outillage ajoutées par upgrade
    bind.execute(
        sa.text(
            "DELETE FROM tarif_poste WHERE cle IN "
            "('outil_base_eur', 'outil_par_trace_eur', 'surcout_forme_speciale_pct')"
        )
    )

    # Drop colonnes ordre_affichage + description sur tarif_poste
    with op.batch_alter_table("tarif_poste") as batch_op:
        batch_op.drop_column("ordre_affichage")
        batch_op.drop_column("description")
