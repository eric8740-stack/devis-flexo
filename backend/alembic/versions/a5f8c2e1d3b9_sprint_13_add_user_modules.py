"""Sprint 13 — Lot S13.A : activation modulaire FlexoCompare / FlexoCheck.

Ajoute 2 booléens sur la table user :
- has_flexocompare : accès au module devis intelligent (cœur historique)
- has_flexocheck : accès au module IA qualité standalone

Default TRUE sur les rows existantes → zéro régression pour le compte demo
Eric et les éventuels users de test déjà en BDD : ils gardent l'accès à
toute l'app. Les nouveaux comptes créés via /api/auth/register hériteront
de TRUE / TRUE également (comportement Sprint 13 = bundle FlexoSuite par
défaut). Les flags pourront ensuite être pilotés finement par Stripe au
Sprint 18 lors de l'ouverture commerciale.

SQLite parity : le batch_alter_table est entouré d'un toggle FK OFF/ON
(idem migration 3f8a1e2c5b94 Sprint 12) pour éviter les conflits ALTER
TABLE en présence de FK CASCADE sur user.entreprise_id.

Revision ID: a5f8c2e1d3b9
Revises: 3f8a1e2c5b94
Create Date: 2026-05-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5f8c2e1d3b9"
down_revision: Union[str, Sequence[str], None] = "3f8a1e2c5b94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # SQLite : désactiver FK pour permettre le batch_alter_table en présence
    # de la FK CASCADE user.entreprise_id → entreprise.id (cf. Sprint 12-A).
    if is_sqlite:
        op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("user") as batch_op:
        # server_default="1" : toutes les rows existantes deviennent TRUE,
        # ce qui préserve l'accès complet pour Eric admin et tout user créé
        # avant la migration. NOT NULL pour ne pas avoir à gérer un état
        # ternaire null/true/false côté code.
        batch_op.add_column(
            sa.Column(
                "has_flexocompare",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_flexocheck",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("has_flexocheck")
        batch_op.drop_column("has_flexocompare")

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=ON")
