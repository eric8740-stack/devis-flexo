"""Brief #30 — refonte porte_cliche : drop ancien schéma + nouveau schéma + reseed.

Le modèle PorteCliche livré en PR #29 portait des champs absurdes pour la
flexo étroite (marque commerciale, matière, laize utile en mm). La sémantique
métier réelle : porte-cliché = cylindre engrenage synchronisé au cyl
magnétique. Cardinalité = 1 par couple (machine × cyl mag), `quantite` =
exemplaires identiques montés.

Stratégie : drop_table + create_table (refonte complète, le modèle est
récent de PR #29, aucun user n'a saisi de PC custom — c'était juste 3
seeds absurdes en compte demo). Migration multi-dialect via op.get_bind()
pour le seed.

Schéma nouveau (cohérent LotProduction Sprint 13) :
  - machine_id     → machine_imprimerie.id
  - cylindre_id    → cylindre_magnetique.id
  - quantite       (NOT NULL, default applicatif = nb_groupes_couleurs)
  - UniqueConstraint(entreprise_id, machine_id, cylindre_id)
  - CheckConstraint(quantite >= 0)

Seed compte demo (entreprise_id=1) : 21 cyl actifs × 3 machines actives =
63 PC, chacun avec `quantite = machine.nb_groupes_couleurs` (fallback 8
si NULL, défensif).

Revision ID: h7d2e6f4a9c3
Revises: g8a4f9c2e5b1
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "h7d2e6f4a9c3"
down_revision: Union[str, Sequence[str], None] = "g8a4f9c2e5b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop l'ancienne table porte_cliche (jette les 3 seeds absurdes
    #    PC-220 Rotec / PC-330 DuPont Cyrel Fast / PC-410 Flint au passage).
    op.drop_index("ix_porte_cliche_entreprise", table_name="porte_cliche")
    op.drop_table("porte_cliche")

    # 2. Recréer avec le nouveau schéma métier.
    op.create_table(
        "porte_cliche",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "entreprise_id",
            sa.Integer(),
            sa.ForeignKey("entreprise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "machine_id",
            sa.Integer(),
            sa.ForeignKey("machine_imprimerie.id"),
            nullable=False,
        ),
        sa.Column(
            "cylindre_id",
            sa.Integer(),
            sa.ForeignKey("cylindre_magnetique.id"),
            nullable=False,
        ),
        sa.Column("quantite", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "actif", sa.Boolean(), nullable=False, server_default=sa.true()
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
            "machine_id",
            "cylindre_id",
            name="uq_porte_cliche_entreprise_machine_cyl",
        ),
        sa.CheckConstraint(
            "quantite >= 0", name="ck_porte_cliche_quantite_positive"
        ),
    )
    op.create_index(
        "ix_porte_cliche_entreprise", "porte_cliche", ["entreprise_id"]
    )

    # 3. Seed compte demo : 21 cyl × 3 machines actives.
    # Insertion idempotente (en théorie inutile car table neuve, mais
    # défensif en cas de replay) : ON CONFLICT non supporté SQLite < 3.24,
    # on utilise un loop Python + INSERT simple. UniqueConstraint protège
    # de toutes façons.
    bind = op.get_bind()
    cyls = bind.execute(
        sa.text(
            "SELECT id FROM cylindre_magnetique "
            "WHERE entreprise_id = 1 AND actif = true "
            "ORDER BY developpe_mm"
        )
    ).fetchall()
    machines = bind.execute(
        sa.text(
            "SELECT id, COALESCE(nb_groupes_couleurs, 8) AS nb "
            "FROM machine_imprimerie "
            "WHERE entreprise_id = 1 AND actif = true"
        )
    ).fetchall()
    for m in machines:
        for c in cyls:
            bind.execute(
                sa.text(
                    "INSERT INTO porte_cliche "
                    "(entreprise_id, machine_id, cylindre_id, quantite, actif) "
                    "VALUES (1, :mid, :cid, :qty, :actif)"
                ),
                {
                    "mid": m.id,
                    "cid": c.id,
                    "qty": int(m.nb),
                    "actif": True,
                },
            )


def downgrade() -> None:
    # Restaurer l'ancien schéma minimal pour permettre un rollback propre.
    # On NE restaure PAS les 3 seeds absurdes — ils étaient une erreur
    # métier et leur retour casserait la cohérence.
    op.drop_index("ix_porte_cliche_entreprise", table_name="porte_cliche")
    op.drop_table("porte_cliche")
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
            "actif", sa.Boolean(), nullable=False, server_default=sa.true()
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
