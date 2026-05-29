"""Phase 2 Lot 4a — ConfigCouts : 7 colonnes P1/P3/P4/P6 + UPDATE démo legacy.

Ajoute les 7 tarifs P1/P3/P4/P6 sur la table `config_couts` (Stratégique,
Phase 1) pour les passer en config par tenant — miroir de Lot 3 sur P5/P7.

Schéma additif et réversible :
  - marge_confort_roulage_mm        Integer        default 10
  - cliche_prix_couleur_eur         Numeric(8,2)   default 30.00
  - outil_base_eur                  Numeric(10,2)  default 150.00
  - outil_par_trace_eur             Numeric(8,2)   default 40.00
  - surcout_forme_speciale_facteur  Numeric(4,2)   default 1.30
                                                   (multiplicateur direct)
  - calage_forfait_eur              Numeric(10,2)  default 180.00
  - finitions_prix_m2_eur           Numeric(8,4)   default 0.1000

Defaults = template neutre (pattern Lot 3) pour les nouveaux tenants. Les
rows existantes (notamment le tenant démo entreprise_id=1) reçoivent les
DEFAULTs lors de l'ALTER TABLE puis sont UPDATE-ées aux valeurs ICE legacy
(10 / 45 / 200 / 50 / 1.40 / 225 / 0.1250) pour préserver les sacrés EXACT
du benchmark (V1a 1 449,09 €, V1b 1 921,09 €, …).

`TarifPoste` correspondants (cliche_prix_couleur, outil_base_eur,
outil_par_trace_eur, surcout_forme_speciale_pct, calage_forfait,
finitions_prix_m2, marge_confort_roulage_mm) sont **conservés en base** —
dépréciation progressive comme Lot 3, plus consommés côté cost_engine.

Multi-tenant : la lecture passe par `get_config_couts_or_raise(db,
entreprise_id)` (scope strict, mirror Lot 2/3).

Revision ID: x8m1h2f6c4e9
Revises: w7l9g1e5d3f8
Create Date: 2026-05-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "x8m1h2f6c4e9"
down_revision: Union[str, Sequence[str], None] = "w7l9g1e5d3f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Valeurs legacy ICE pour le tenant démo (entreprise_id=1) — préservent
# les sacrés EXACT (V1a 1 449,09 €, etc.).
_DEMO_LEGACY = {
    "marge_confort_roulage_mm": 10,
    "cliche_prix_couleur_eur": 45.00,
    "outil_base_eur": 200.00,
    "outil_par_trace_eur": 50.00,
    "surcout_forme_speciale_facteur": 1.40,
    "calage_forfait_eur": 225.00,
    "finitions_prix_m2_eur": 0.1250,
}


def upgrade() -> None:
    # ── Schéma : ajout des 7 colonnes (NOT NULL avec server_default pour
    # absorber les rows existantes ; la même valeur sert de default template).
    op.add_column(
        "config_couts",
        sa.Column(
            "marge_confort_roulage_mm",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "cliche_prix_couleur_eur",
            sa.Numeric(8, 2),
            nullable=False,
            server_default="30.00",
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "outil_base_eur",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="150.00",
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "outil_par_trace_eur",
            sa.Numeric(8, 2),
            nullable=False,
            server_default="40.00",
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "surcout_forme_speciale_facteur",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.30",
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "calage_forfait_eur",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="180.00",
        ),
    )
    op.add_column(
        "config_couts",
        sa.Column(
            "finitions_prix_m2_eur",
            sa.Numeric(8, 4),
            nullable=False,
            server_default="0.1000",
        ),
    )

    # ── Données : UPDATE du tenant démo (entreprise_id=1) aux valeurs legacy
    # ICE. Scope strict — préserve les sacrés EXACT et l'isolation multi-tenant.
    _config_couts = sa.table(
        "config_couts",
        sa.column("entreprise_id", sa.Integer),
        sa.column("marge_confort_roulage_mm", sa.Integer),
        sa.column("cliche_prix_couleur_eur", sa.Numeric),
        sa.column("outil_base_eur", sa.Numeric),
        sa.column("outil_par_trace_eur", sa.Numeric),
        sa.column("surcout_forme_speciale_facteur", sa.Numeric),
        sa.column("calage_forfait_eur", sa.Numeric),
        sa.column("finitions_prix_m2_eur", sa.Numeric),
    )
    op.execute(
        _config_couts.update()
        .where(_config_couts.c.entreprise_id == 1)
        .values(**_DEMO_LEGACY)
    )


def downgrade() -> None:
    # Drop des 7 colonnes. La donnée legacy injectée dans l'UPDATE est perdue
    # avec la colonne — comportement attendu sur une migration additive.
    op.drop_column("config_couts", "finitions_prix_m2_eur")
    op.drop_column("config_couts", "calage_forfait_eur")
    op.drop_column("config_couts", "surcout_forme_speciale_facteur")
    op.drop_column("config_couts", "outil_par_trace_eur")
    op.drop_column("config_couts", "outil_base_eur")
    op.drop_column("config_couts", "cliche_prix_couleur_eur")
    op.drop_column("config_couts", "marge_confort_roulage_mm")
