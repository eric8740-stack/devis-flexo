"""B3b — DROP COLUMN machine.vitesse_pratique_m_min (cleanup post-B3a).

Contexte : la colonne `machine.vitesse_pratique_m_min` a été ajoutée par
B1 (migration `z0p4n6r8s1t3`) puis :
  - B2 (#81) l'a retirée de l'API publique (MachineCreate/Update/Read)
    et de l'UI MachineForm. Decision actee : une seule vitesse reelle =
    `vitesse_moyenne_m_h / 60`.
  - B3a (#82) a repointé `optimisation_loader.charger_machines_actives`
    sur `Machine`, en dérivant `vitesse_pratique_m_min` à la volée :
    `round(vitesse_moyenne_m_h / 60)`. La colonne DB n'est plus consommée
    par aucune logique applicative (vérifié par grep B3b).

B3b clôture la dépréciation en supprimant la colonne morte. Réversible :
le downgrade recrée la colonne `Integer NULL` (sans peupler de données
historiques -- la valeur dérivée à la volée reste le contrat depuis B2).

SACRED preserve :
  - cost_engine : aucune logique modifiée. La colonne n'alimentait plus
    rien depuis B3a.
  - Benchmark V1a 1 449,09 EUR + 5 cas + V8 : 13/13 EXACT (fixture
    in-memory dans `test_cost_engine_5cas_benchmark.py`, indépendante
    du schéma BDD live).
  - Multi-tenant strict, `vitesse_moyenne_m_h` (m/h, SACRED) intact.

HORS PERIMETRE B3b :
  - Table `machine_imprimerie` conservée (FK historiques
    `lot_production.machine_id`, `porte_cliche.machine_id`).
  - Repoint `crud.devis._construire_devis_input_pour_lot` qui lit encore
    `MachineImprimerie.laize_utile_mm` pour le chiffrage multi-lots
    (SACRED) -- sprint dédié ulterieur.

Revision ID: a1b2c3d4e5f6
Revises: z0p4n6r8s1t3
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "z0p4n6r8s1t3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop simple sur Postgres (ALTER TABLE ... DROP COLUMN natif). Sur
    # SQLite (dev/tests), batch_alter_table recree la table sans la colonne.
    with op.batch_alter_table("machine", schema=None) as batch:
        batch.drop_column("vitesse_pratique_m_min")


def downgrade() -> None:
    # Recree la colonne `Integer NULL` (sans peupler de donnees historiques :
    # la valeur derivée a la volee `vitesse_moyenne_m_h / 60` reste le
    # contrat depuis B2 et B3a -- la colonne n'est plus lue par
    # l'application). Si necessaire, repeupler manuellement post-downgrade.
    with op.batch_alter_table("machine", schema=None) as batch:
        batch.add_column(
            sa.Column(
                "vitesse_pratique_m_min",
                sa.Integer(),
                nullable=True,
            )
        )
