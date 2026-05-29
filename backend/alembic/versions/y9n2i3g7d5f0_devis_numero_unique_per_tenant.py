"""Fix 409 — UNIQUE(devis.numero) scope tenant + reseau de garde anti-doublon.

Contexte : `generate_next_numero` utilisait `count(*) + 1` (MVP Sprint 4) sans
scope tenant. Après hard-delete d'un devis, le compteur regenerait un numero
deja attribue -> UniqueViolation sur `ix_devis_numero` -> 409 cote client.
Repro deterministe : `backend/scripts/repro_409_devis_numero.py`.

Fix de schema :
  - drop UNIQUE INDEX global `ix_devis_numero` (cree au Sprint 4, identique
    sur SQLite et Postgres : `CREATE UNIQUE INDEX ix_devis_numero ON devis (numero)`).
  - create UNIQUE INDEX composite `ix_devis_entreprise_id_numero` sur
    (entreprise_id, numero). Permet aussi que deux tenants aient chacun
    DEV-2026-0001 sans collision cross-tenant.

Garde-fou : pre-check de doublons (entreprise_id, numero) **avant** toute
modification de schema. Si > 0, on raise pour stopper la migration proprement
sans laisser la base dans un etat intermediaire. Cas attendu : 0 doublon (la
contrainte globale en empechait la creation).

Reversible : downgrade restaure l'UNIQUE INDEX global sur numero.

Revision ID: y9n2i3g7d5f0
Revises: x8m1h2f6c4e9
Create Date: 2026-05-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


revision: str = "y9n2i3g7d5f0"
down_revision: Union[str, Sequence[str], None] = "x8m1h2f6c4e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _check_no_duplicate_entreprise_numero(bind: sa.Connection) -> None:
    """Stoppe la migration si la base contient deja des (entreprise_id, numero)
    en double. La contrainte UNIQUE globale sur `numero` rendait ce cas
    impossible jusqu'ici ; on garde le filet pour les futurs replays."""
    rows = bind.execute(
        text(
            """
            SELECT entreprise_id, numero, COUNT(*) AS n
            FROM devis
            GROUP BY entreprise_id, numero
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if rows:
        sample = [(r[0], r[1], r[2]) for r in rows[:5]]
        raise RuntimeError(
            "Migration y9n2i3g7d5f0 annulee : "
            f"{len(rows)} doublons (entreprise_id, numero) detectes en base. "
            f"Exemples : {sample}. "
            "Nettoyer la donnee avant de relancer `alembic upgrade head`."
        )


def upgrade() -> None:
    bind = op.get_bind()
    _check_no_duplicate_entreprise_numero(bind)

    # Drop l'UNIQUE INDEX global sur numero. Nom uniforme SQLite/Postgres car
    # cree par `op.create_index(op.f('ix_devis_numero'), ..., unique=True)`
    # dans la migration Sprint 4 (b89d835f3823).
    op.drop_index("ix_devis_numero", table_name="devis")

    # Cree l'UNIQUE INDEX composite scope tenant. Sert aussi a accelerer
    # `WHERE entreprise_id = X AND numero LIKE 'DEV-YYYY-%'` (utilise par
    # `generate_next_numero` apres ce fix).
    op.create_index(
        "ix_devis_entreprise_id_numero",
        "devis",
        ["entreprise_id", "numero"],
        unique=True,
    )


def downgrade() -> None:
    # Sens inverse : on retire le composite et on remet la UNIQUE globale
    # historique. Si la base contient deja deux tenants avec le meme numero
    # (situation possible apres le fix), le downgrade va echouer cote DB
    # avec une UniqueViolation -- c'est le comportement attendu (pas de
    # silent data loss).
    op.drop_index("ix_devis_entreprise_id_numero", table_name="devis")
    op.create_index(
        "ix_devis_numero",
        "devis",
        ["numero"],
        unique=True,
    )
