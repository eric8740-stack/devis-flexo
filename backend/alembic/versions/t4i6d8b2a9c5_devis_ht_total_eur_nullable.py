"""Sprint 16 fix chiffrage — rend devis.ht_total_eur nullable.

Décision produit (option B) : un devis dont le chiffrage automatique
échoue (ex: matière du lot non reliée à un complexe de coût) est créé
en état "chiffrage incomplet" — `ht_total_eur = NULL` +
`payload_output.chiffrage_auto_erreur` rempli — au lieu d'un 0 €
trompeur ou d'un rejet de la création.

`ht_total_eur` était `Numeric(10,2) NOT NULL`. On le passe nullable.
Justification métier : un devis non chiffré n'a légitimement pas de
total HT — NULL exprime "non calculé", distinct de 0 € (= gratuit).

SQLite : `alter_column` via `batch_alter_table` (DROP+COPY+RENAME).
Toggle `PRAGMA foreign_keys=OFF/ON` car la table `devis` a des FK
incoming (lot_production.devis_id, controle_bat.devis_id, etc.) qui
bloqueraient le DROP. Le listener checkout (fix/pragma-foreign-keys-
checkout, déjà mergé) re-force FK=ON au retour de connexion au pool —
aucun leak résiduel.

PostgreSQL : ALTER COLUMN DROP NOT NULL natif, pas de toggle.

Aucune donnée modifiée : les devis existants gardent leur ht_total_eur
courant. Seule la contrainte de nullabilité change.

Revision ID: t4i6d8b2a9c5
Revises: s3h5c7d9f4e1
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "t4i6d8b2a9c5"
down_revision: Union[str, Sequence[str], None] = "s3h5c7d9f4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("devis") as batch_op:
        batch_op.alter_column(
            "ht_total_eur",
            existing_type=sa.Numeric(10, 2),
            nullable=True,
        )

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    """Repasse ht_total_eur en NOT NULL.

    ⚠️ Échoue si des devis "chiffrage incomplet" (ht_total_eur NULL)
    existent en base — il faudrait d'abord leur affecter une valeur.
    Acceptable : downgrade rare, sur DB de dev/test sans données NULL.
    """
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("devis") as batch_op:
        batch_op.alter_column(
            "ht_total_eur",
            existing_type=sa.Numeric(10, 2),
            nullable=False,
        )

    if is_sqlite:
        op.execute("PRAGMA foreign_keys=ON")
