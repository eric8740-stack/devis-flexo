"""Ré-alignement ICE de config_couts pour le compte démo (entreprise_id=1).

Contexte : la ligne `config_couts` du tenant démo créée AVANT que le seed ne
porte les valeurs ICE (ou via onboarding aux defaults template du modèle
50/25/35) n'a jamais été ré-alignée pour 3 champs Phase 1/Lot 2/Lot 3 :

    marge_standard_pct              35  ->  18
    cout_exploitation_machine_eur_h 50  -> 375
    cout_operateur_eur_h            25  ->  70

La migration Phase 1 `w7l9g1e5d3f8` ne fait que créer les tables (aucun
backfill) ; seule la Lot 4a `x8m1h2f6c4e9` a UPDATE entreprise_id=1, mais
uniquement ses 7 propres champs. D'où le trou : sur la ligne PROD pré-existante
ces 3 champs sont restés au server_default -> la page devis rend 1 347,35 €
au lieu du sacré 1 449,09 €. Local/CI = OK car re-seed frais
(cf scripts/seed.py:388 qui pose déjà 18/375/70 sur DEMO_ENTREPRISE_ID).

Vérif arithmétique : coût de revient ICE 1 228,04 € × 1,18 = 1 449,09 € (V1a).

Idempotente (re-run = mêmes valeurs ; 0 ligne touchée si absente = safe).
SCOPE STRICT entreprise_id=1 : ne touche AUCUN autre tenant (chaque imprimeur
a ses propres marges/coûts horaires). Aucune modification de logique
cost_engine ni de seed (le seed est déjà correct).

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6g7
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Valeurs ICE historiques — miroir de scripts/seed.py (DEMO_ENTREPRISE_ID).
# Maintenir en synchro si le seed démo évolue.
_DEMO_ICE = {
    "marge_standard_pct": 18,
    "cout_exploitation_machine_eur_h": 375,
    "cout_operateur_eur_h": 70,
}


def upgrade() -> None:
    _config_couts = sa.table(
        "config_couts",
        sa.column("entreprise_id", sa.Integer),
        sa.column("marge_standard_pct", sa.Numeric),
        sa.column("cout_exploitation_machine_eur_h", sa.Numeric),
        sa.column("cout_operateur_eur_h", sa.Numeric),
    )
    op.execute(
        _config_couts.update()
        .where(_config_couts.c.entreprise_id == 1)
        .values(**_DEMO_ICE)
    )


def downgrade() -> None:
    # No-op VOLONTAIRE : ne PAS réintroduire les defaults template erronés
    # (35/50/25) qui cassent le sacré V1a 1 449,09 €. La valeur ICE est la
    # bonne donnée métier pour le compte démo ; un downgrade qui la défait
    # n'a pas de sens et corromprait le benchmark.
    pass
