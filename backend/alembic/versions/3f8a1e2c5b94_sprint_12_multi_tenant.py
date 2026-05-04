"""Sprint 12 multi-tenant — add user table + scope all tables by entreprise

Revision ID: 3f8a1e2c5b94
Revises: 7c2e4d1f9a3b
Create Date: 2026-05-04 14:00:00.000000

Sprint 12 MVP multi-tenant — fondation auth + scope par entreprise.

Changements de schéma :

1. Nouvelle table `user` (1-to-1 vers entreprise via FK UNIQUE).
2. `entreprise` : ajout `is_demo: Boolean DEFAULT FALSE`. UPDATE id=1
   (Paysant) en is_demo=TRUE si la ligne existe — sans erreur si DB
   fraîche.
3. Sur 14 tables métier : ajout `entreprise_id` NOT NULL FK CASCADE + index.
   Backfill = 1 (compte demo Eric) pour tous les records existants. Le
   compte demo hérite ainsi des 148 records seedés (3 machines, 31 complexes,
   etc.). Toute nouvelle inscription via /api/auth/register créera un tenant
   vierge (Sprint 12-B).

Le compte admin Eric (user is_admin=True) est créé par `scripts/seed.py`
fonction `seed_user_admin()`, **PAS par cette migration**. Raison : la
migration peut être appliquée sur une DB fraîche (alembic upgrade head
sans seed préalable) où entreprise id=1 n'existe pas encore — un INSERT
user FK CASCADE échouerait. Le seed connaît cette dépendance d'ordre et
crée entreprise PUIS user.

Procédure prod Railway :
  1. Push main → CI verte → Railway redeploy auto
  2. Boot container : `alembic upgrade head` applique cette migration
  3. Eric run `python -m scripts.seed` via DATABASE_PUBLIC_URL inline
     (procédure standard Note 6) qui crée entreprise + user admin

Variables d'env Railway requises avant push prod :
  - ADMIN_INITIAL_EMAIL=admin@devis-flexo.fr
  - ADMIN_INITIAL_PASSWORD=<choisi par Eric, hashé bcrypt par seed.py>
  - JWT_SECRET=<généré aléatoirement, 64 chars min — Lot S12-B>
  - SENDGRID_API_KEY=<créé compte SendGrid — Lot S12-B>
  - APP_BASE_URL=https://devis-flexo.vercel.app

Roundtrip upgrade/downgrade testé en local SQLite avec batch_alter_table
(SQLite ne supporte pas ALTER COLUMN nativement).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f8a1e2c5b94"
down_revision: Union[str, Sequence[str], None] = "7c2e4d1f9a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 14 tables métier scopées par entreprise_id (cf. brief Sprint 12 §3.3).
# `correspondance_laize_metrage` reste globale (réf physique 33 lignes,
# brief §3.4 D4). `entreprise` ne se scope pas elle-même.
_TABLES_TO_SCOPE = [
    "client",
    "fournisseur",
    "machine",
    "complexe",
    "catalogue",
    "operation_finition",
    "partenaire_st",
    "outil_decoupe",
    "charge_mensuelle",
    "charge_machine_mensuelle",
    "tarif_encre",
    "tarif_poste",
    "temps_operation_standard",
    "devis",
]

DEMO_ENTREPRISE_ID = 1


def upgrade() -> None:
    """Upgrade schema — Sprint 12 multi-tenant."""
    bind = op.get_bind()

    # ------------------------------------------------------------
    # 1. Création table user
    # ------------------------------------------------------------
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nom_contact", sa.String(150), nullable=False),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("email_confirmation_token", sa.String(255), nullable=True),
        sa.Column(
            "email_confirmation_expires", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("password_reset_token", sa.String(255), nullable=True),
        sa.Column(
            "password_reset_expires", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "date_creation",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "date_derniere_connexion", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_index(
        "ix_user_entreprise_id", "user", ["entreprise_id"], unique=True
    )

    # ------------------------------------------------------------
    # 2. Ajout is_demo sur entreprise + UPDATE id=1 → True
    # ------------------------------------------------------------
    with op.batch_alter_table("entreprise") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_demo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    bind.execute(
        sa.text("UPDATE entreprise SET is_demo = TRUE WHERE id = :did"),
        {"did": DEMO_ENTREPRISE_ID},
    )

    # ------------------------------------------------------------
    # 3. Sur 14 tables métier : add entreprise_id NULLABLE + backfill +
    #    SET NOT NULL + FK CASCADE + index
    # ------------------------------------------------------------
    for table_name in _TABLES_TO_SCOPE:
        # 3.a Ajouter colonne nullable temporaire
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column("entreprise_id", sa.Integer(), nullable=True)
            )

        # 3.b Backfill = 1 (compte demo Eric)
        bind.execute(
            sa.text(
                f"UPDATE {table_name} SET entreprise_id = :did"  # noqa: S608
            ),
            {"did": DEMO_ENTREPRISE_ID},
        )

        # 3.c SET NOT NULL + FK CASCADE + index
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("entreprise_id", nullable=False)
            batch_op.create_foreign_key(
                f"fk_{table_name}_entreprise",
                "entreprise",
                ["entreprise_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(
                f"ix_{table_name}_entreprise_id", ["entreprise_id"]
            )

    # NOTE : aucune INSERT user ici. Le compte admin Eric est créé par
    # `scripts/seed.py` fonction `seed_user_admin()` qui sait gérer la
    # dépendance d'ordre (entreprise existe AVANT user).


def downgrade() -> None:
    """Downgrade schema — symétrique."""
    # NOTE : pas de DELETE user explicite — le drop_table de l'étape 1
    # finale supprime aussi toutes les lignes.

    # 3. Drop entreprise_id sur les 14 tables métier (ordre inverse)
    for table_name in reversed(_TABLES_TO_SCOPE):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_entreprise_id")
            batch_op.drop_constraint(
                f"fk_{table_name}_entreprise", type_="foreignkey"
            )
            batch_op.drop_column("entreprise_id")

    # 2. Drop is_demo sur entreprise
    with op.batch_alter_table("entreprise") as batch_op:
        batch_op.drop_column("is_demo")

    # 1. Drop table user
    op.drop_index("ix_user_entreprise_id", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")
