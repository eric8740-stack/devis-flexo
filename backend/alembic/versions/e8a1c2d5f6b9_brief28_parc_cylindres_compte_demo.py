"""Brief #28 — parc cylindres compte demo (désactivations + ajouts).

Mise à jour du parc cylindres pour le compte demo (entreprise_id=1) :
  - Désactivations (actif=False, suppression douce → préserve FK devis
    historiques) : 72, 90, 103 dents.
  - Ajouts (actif=True, idempotent) : 101, 106, 120, 148, 187 dents.

Conversion dents → mm via DENTS_TO_MM_FACTOR = 3.175. Les valeurs sont
arrondies à 2 décimales (Numeric(6, 2)) pour matcher la colonne
`developpe_mm`.

Pour la robustesse multi-dialect (Postgres prod + SQLite tests), on
exécute toutes les opérations via SQLAlchemy `op.get_bind()` plutôt
qu'avec du SQL natif.

Cylindre 132 dents : préservé actif (mentionné explicitement dans le
brief comme "NE PAS désactiver").

Revision ID: e8a1c2d5f6b9
Revises: d3f1a8e6c5b2
Create Date: 2026-05-19
"""
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e8a1c2d5f6b9"
down_revision: Union[str, Sequence[str], None] = "d3f1a8e6c5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DENTS_DESACTIVER = (72, 90, 103)
DENTS_AJOUTER = (101, 106, 120, 148, 187)
DENTS_TO_MM = Decimal("3.175")


def _dents_to_mm(dents: int) -> float:
    """Conversion dents → mm arrondie à 2 décimales (matche Numeric(6, 2))."""
    return float((Decimal(dents) * DENTS_TO_MM).quantize(Decimal("0.01")))


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Désactivations (suppression douce) — match large sur developpe_mm
    # avec tolérance arrondi côté float vs Numeric. ROUND() Postgres = round
    # half away from zero ; SQLite round half to even. Tolérance ±0.005 mm.
    for dents in DENTS_DESACTIVER:
        mm = _dents_to_mm(dents)
        bind.execute(
            sa.text(
                "UPDATE cylindre_magnetique SET actif = :actif "
                "WHERE entreprise_id = 1 "
                "AND developpe_mm BETWEEN :mm_min AND :mm_max"
            ),
            {
                "actif": False,
                "mm_min": mm - 0.01,
                "mm_max": mm + 0.01,
            },
        )

    # 2. Ajouts idempotents — INSERT IF NOT EXISTS (via SELECT) pour
    # support cross-dialect.
    for dents in DENTS_AJOUTER:
        mm = _dents_to_mm(dents)
        existant = bind.execute(
            sa.text(
                "SELECT id FROM cylindre_magnetique "
                "WHERE entreprise_id = 1 "
                "AND developpe_mm BETWEEN :mm_min AND :mm_max"
            ),
            {"mm_min": mm - 0.01, "mm_max": mm + 0.01},
        ).first()
        if existant is None:
            bind.execute(
                sa.text(
                    "INSERT INTO cylindre_magnetique "
                    "(entreprise_id, developpe_mm, "
                    " nb_pc_10p, nb_pc_13p, nb_pc_2200, nb_pc_p5, actif) "
                    "VALUES (1, :mm, 0, 0, 0, 0, :actif)"
                ),
                {"mm": mm, "actif": True},
            )


def downgrade() -> None:
    bind = op.get_bind()

    # 1. Supprimer les cylindres ajoutés (DELETE par dents).
    for dents in DENTS_AJOUTER:
        mm = _dents_to_mm(dents)
        bind.execute(
            sa.text(
                "DELETE FROM cylindre_magnetique "
                "WHERE entreprise_id = 1 "
                "AND developpe_mm BETWEEN :mm_min AND :mm_max"
            ),
            {"mm_min": mm - 0.01, "mm_max": mm + 0.01},
        )

    # 2. Réactiver les cylindres désactivés.
    for dents in DENTS_DESACTIVER:
        mm = _dents_to_mm(dents)
        bind.execute(
            sa.text(
                "UPDATE cylindre_magnetique SET actif = :actif "
                "WHERE entreprise_id = 1 "
                "AND developpe_mm BETWEEN :mm_min AND :mm_max"
            ),
            {
                "actif": True,
                "mm_min": mm - 0.01,
                "mm_max": mm + 0.01,
            },
        )
