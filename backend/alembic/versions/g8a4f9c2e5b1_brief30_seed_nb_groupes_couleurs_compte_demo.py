"""Brief #30 — seed nb_groupes_couleurs compte demo.

Garantit que les machines du compte demo (entreprise_id=1) ont une valeur
de `nb_groupes_couleurs` cohérente avec le catalogue par défaut Sprint 13
(cf `app/data/catalogue_defaults.py`).

Nécessaire pour le commit 3 qui seede les porte-clichés avec
`quantite = machine.nb_groupes_couleurs` — un NULL ici casserait l'INSERT.

Migration data-only idempotente. Schéma `MachineImprimerie` inchangé
(`nb_groupes_couleurs: Mapped[int | None]` reste nullable, on ne change
pas la contrainte pour rester rétro-compatible avec les tenants ayant
fait l'onboarding plus tôt).

UPDATE conditionnel uniquement quand `nb_groupes_couleurs IS NULL` —
on ne touche pas les valeurs déjà saisies par l'imprimeur (souveraineté
commerciale).

Revision ID: g8a4f9c2e5b1
Revises: f4b7e3a9c1d6
Create Date: 2026-05-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "g8a4f9c2e5b1"
down_revision: Union[str, Sequence[str], None] = "f4b7e3a9c1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Valeurs canoniques du catalogue par défaut Sprint 13 (cf
# `app/data/catalogue_defaults.py` MACHINES_DEFAULT). Maintenir en synchro.
SEEDS_NB_COULEURS = [
    ("Mark Andy 2200", 8),
    ("OMET XFlex 330", 10),
    ("Nilpeter FA-22", 8),
]


def upgrade() -> None:
    bind = op.get_bind()
    # UPDATE conditionnel : seulement les machines compte demo avec
    # nb_groupes_couleurs NULL. Ne touche pas les valeurs déjà saisies.
    for nom, nb in SEEDS_NB_COULEURS:
        bind.execute(
            sa.text(
                "UPDATE machine_imprimerie "
                "SET nb_groupes_couleurs = :nb "
                "WHERE entreprise_id = 1 "
                "AND nom = :nom "
                "AND nb_groupes_couleurs IS NULL"
            ),
            {"nb": nb, "nom": nom},
        )


def downgrade() -> None:
    # Pas de downgrade utile : les valeurs canoniques métier sont
    # nécessaires au bon fonctionnement de l'app multi-lots. Laisser un
    # noop permet de revenir au state précédent sans casser le seed.
    pass
