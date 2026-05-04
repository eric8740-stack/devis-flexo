"""Widen tarif_poste valeur_min/valeur_max bounds

Revision ID: 7c2e4d1f9a3b
Revises: 5a1e9b20c4f8
Create Date: 2026-05-04 09:00:00.000000

Mini-sprint Notes 15+16+bornes (04/05/2026) — élargissement des
bornes valeur_min / valeur_max sur les 10 paramètres tarif_poste pour
permettre aux imprimeurs testeurs LinkedIn de configurer leurs
tarifs propres (Eric a remonté que cliche_prix_couleur plafonné à 60 €
était trop juste — certaines entreprises facturent 80-90 €).

Aucune valeur_defaut n'est modifiée. Les bornes sont juste élargies
pour augmenter la plage acceptée par PUT /api/tarif-poste/{cle}.

Migration data-only :
- 10 UPDATEs sur les lignes existantes (tarif_poste.cle uniques)
- Pas de modif de schéma
- Downgrade restaure les bornes Sprint 9 v2 d'origine
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c2e4d1f9a3b"
down_revision: Union[str, Sequence[str], None] = "5a1e9b20c4f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (cle, nouvelle valeur_min, nouvelle valeur_max)
_BORNES_NOUVELLES = [
    ("matiere_prix_kg_defaut", 0.8000, 5.0000),
    ("cliche_prix_couleur", 25.0000, 100.0000),
    ("calage_forfait", 100.0000, 600.0000),
    ("roulage_prix_horaire", 200.0000, 800.0000),
    ("marge_confort_roulage_mm", 5.0000, 30.0000),
    ("finitions_prix_m2", 0.0300, 0.5000),
    ("mo_prix_horaire", 40.0000, 120.0000),
    ("outil_base_eur", 80.0000, 800.0000),
    ("outil_par_trace_eur", 15.0000, 250.0000),
    ("surcout_forme_speciale_pct", 1.0000, 3.0000),
]

# (cle, ancienne valeur_min, ancienne valeur_max) — pour downgrade
_BORNES_ANCIENNES = [
    ("matiere_prix_kg_defaut", 1.0000, 2.5000),
    ("cliche_prix_couleur", 30.0000, 60.0000),
    ("calage_forfait", 150.0000, 300.0000),
    ("roulage_prix_horaire", 250.0000, 500.0000),
    ("marge_confort_roulage_mm", 5.0000, 20.0000),
    ("finitions_prix_m2", 0.0500, 0.2000),
    ("mo_prix_horaire", 50.0000, 90.0000),
    ("outil_base_eur", 100.0000, 500.0000),
    ("outil_par_trace_eur", 20.0000, 150.0000),
    ("surcout_forme_speciale_pct", 1.0000, 2.0000),
]


def upgrade() -> None:
    """Élargit les bornes des 10 paramètres tarif_poste."""
    bind = op.get_bind()
    for cle, vmin, vmax in _BORNES_NOUVELLES:
        bind.execute(
            sa.text(
                "UPDATE tarif_poste SET valeur_min = :vmin, valeur_max = :vmax "
                "WHERE cle = :cle"
            ),
            {"vmin": vmin, "vmax": vmax, "cle": cle},
        )


def downgrade() -> None:
    """Restaure les bornes Sprint 9 v2 d'origine."""
    bind = op.get_bind()
    for cle, vmin, vmax in _BORNES_ANCIENNES:
        bind.execute(
            sa.text(
                "UPDATE tarif_poste SET valeur_min = :vmin, valeur_max = :vmax "
                "WHERE cle = :cle"
            ),
            {"vmin": vmin, "vmax": vmax, "cle": cle},
        )
