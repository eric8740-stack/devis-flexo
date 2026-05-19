"""Brief #29 — table porte_cliche + seed compte demo.

Crée la table `porte_cliche` (sleeves / supports de cliché flexo) et
seede 3 porte-clichés représentatifs pour le compte demo (entreprise_id=1)
afin que le compte démarre "prêt à l'emploi" sans configuration manuelle.

Convention multi-tenant : FK entreprise_id CASCADE. Unique (entreprise_id,
reference). Soft delete via `actif=False` (pas de suppression dure).

Multi-dialect (Postgres prod + SQLite tests) : on exécute toutes les
opérations data via `op.get_bind()` plutôt qu'avec du SQL natif.

Revision ID: f4b7e3a9c1d6
Revises: e8a1c2d5f6b9
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f4b7e3a9c1d6"
down_revision: Union[str, Sequence[str], None] = "e8a1c2d5f6b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEEDS_COMPTE_DEMO = [
    # (reference, marque, modele, laize_utile_mm, diametre_int_mm, matiere)
    ("PC-220", "Rotec", None, 220.00, 76.00, "polyuréthane"),
    ("PC-330", "DuPont Cyrel", "Fast", 330.00, 76.00, "polyuréthane"),
    ("PC-410", "Flint", None, 410.00, 152.00, "carbone"),
]


def upgrade() -> None:
    op.create_table(
        "porte_cliche",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(50), nullable=False),
        sa.Column("marque", sa.String(80), nullable=True),
        sa.Column("modele", sa.String(80), nullable=True),
        sa.Column("laize_utile_mm", sa.Numeric(6, 2), nullable=False),
        sa.Column("diametre_interieur_mm", sa.Numeric(6, 2), nullable=True),
        sa.Column("matiere", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "actif",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "entreprise_id",
            "reference",
            name="uq_porte_cliche_reference_entreprise",
        ),
    )
    op.create_index(
        "ix_porte_cliche_entreprise", "porte_cliche", ["entreprise_id"]
    )

    # Seed compte demo (entreprise_id=1) — idempotent via WHERE NOT EXISTS.
    bind = op.get_bind()
    for ref, marque, modele, laize, diam, matiere in SEEDS_COMPTE_DEMO:
        existant = bind.execute(
            sa.text(
                "SELECT id FROM porte_cliche "
                "WHERE entreprise_id = 1 AND reference = :ref"
            ),
            {"ref": ref},
        ).first()
        if existant is None:
            bind.execute(
                sa.text(
                    "INSERT INTO porte_cliche "
                    "(entreprise_id, reference, marque, modele, "
                    " laize_utile_mm, diametre_interieur_mm, matiere, actif) "
                    "VALUES (1, :ref, :marque, :modele, "
                    " :laize, :diam, :matiere, :actif)"
                ),
                {
                    "ref": ref,
                    "marque": marque,
                    "modele": modele,
                    "laize": laize,
                    "diam": diam,
                    "matiere": matiere,
                    "actif": True,
                },
            )


def downgrade() -> None:
    op.drop_index("ix_porte_cliche_entreprise", table_name="porte_cliche")
    op.drop_table("porte_cliche")
