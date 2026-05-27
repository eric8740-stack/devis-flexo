"""Lot 1 complexe enrichi — données : complète les 31 complexes (entreprise_id=1).

Renseigne, sur les 31 complexes du tenant démo (entreprise_id=1) :
  - grammage_g_m2 des 13 FILMS (épaisseur × densité standard de face :
    BOPP 0.91, PP 0.905, PE 0.92, PVC 1.30). Les papiers gardent leur
    grammage existant (intouché — dont id=31 du benchmark figé).
  - epaisseur_microns : films uniquement (NULL pour les papiers).
  - est_transparent : True si "TRANSPARENT" dans la référence.
  - opacite_pct : défaut documenté par type (transparent 5, film opaque 92,
    papier 95) — à affiner par Eric.
  - sous_type : dérivé de la référence/famille.

certifications_* laissées NULL (non spécifiées au Lot 1).

⚠️ Modifie des données seedées d'entreprise_id=1 (autorisé par le cadrage).
Scopé par reference + entreprise_id=1. Neutre pour le cost_engine Poste 1
(le grammage s'annule : cout = surface × prix_m2) → benchmark 11/11 inchangé.

Réversible : downgrade remet grammage films à NULL et les champs techniques
à leur état antérieur (epaisseur/opacite/sous_type NULL, est_transparent False).

Revision ID: v6k8f0d4c2e7
Revises: u5j7e9c3b1d6
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "v6k8f0d4c2e7"
down_revision: Union[str, Sequence[str], None] = "u5j7e9c3b1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_ENTREPRISE_ID = 1

# (reference, grammage_g_m2, epaisseur_microns, est_transparent, opacite_pct, sous_type)
FILMS = [
    ("BOPP_BLANC_50", 45.5, 50, False, 92.0, "bopp_blanc"),
    ("BOPP_TRANSPARENT_50", 45.5, 50, True, 5.0, "bopp_transparent"),
    ("BOPP_BLANC_70", 63.7, 70, False, 92.0, "bopp_blanc"),
    ("BOPP_RENFORCE_60", 54.6, 60, False, 92.0, "bopp_renforce"),
    ("PP_BLANC_60", 54.3, 60, False, 92.0, "pp_blanc"),
    ("PP_TRANSPARENT_60", 54.3, 60, True, 5.0, "pp_transparent"),
    ("PP_BLANC_80", 72.4, 80, False, 92.0, "pp_blanc"),
    ("PE_BLANC_70", 64.4, 70, False, 92.0, "pe_blanc"),
    ("PE_TRANSPARENT_70", 64.4, 70, True, 5.0, "pe_transparent"),
    ("PE_BLANC_100", 92.0, 100, False, 92.0, "pe_blanc"),
    ("PVC_BLANC_80", 104.0, 80, False, 92.0, "pvc_blanc"),
    ("PVC_BLANC_100", 130.0, 100, False, 92.0, "pvc_blanc"),
    ("PVC_TRANSPARENT_120", 156.0, 120, True, 5.0, "pvc_transparent"),
]

# (reference, sous_type) — grammage INCHANGÉ, epaisseur NULL, opacite 95, opaque
PAPIERS = [
    ("THERMIQUE_60", "thermique_topcoat"),
    ("THERMIQUE_80", "thermique_topcoat"),
    ("THERMIQUE_TOPCOAT_90", "thermique_topcoat"),
    ("COUCHE_BRILLANT_80", "couche_brillant"),
    ("COUCHE_MAT_90", "couche_mat"),
    ("COUCHE_BRILLANT_100", "couche_brillant"),
    ("COUCHE_MAT_120", "couche_mat"),
    ("STD_80", "standard"),
    ("STD_90", "standard"),
    ("STD_100", "standard"),
    ("EPAIS_120", "epais"),
    ("EPAIS_140", "epais"),
    ("EPAIS_160", "epais"),
    ("KRAFT_90", "kraft"),
    ("KRAFT_120", "kraft"),
    ("VERGE_100", "verge"),
    ("VERGE_120", "verge"),
    ("VELIN_STANDARD_80", "velin"),
]

_complexe = sa.table(
    "complexe",
    sa.column("reference", sa.String),
    sa.column("entreprise_id", sa.Integer),
    sa.column("grammage_g_m2", sa.Numeric),
    sa.column("epaisseur_microns", sa.Integer),
    sa.column("est_transparent", sa.Boolean),
    sa.column("opacite_pct", sa.Numeric),
    sa.column("sous_type", sa.String),
)


def _where(ref: str):
    return (_complexe.c.reference == ref) & (
        _complexe.c.entreprise_id == DEMO_ENTREPRISE_ID
    )


def upgrade() -> None:
    for ref, grammage, epaisseur, transp, opacite, sous_type in FILMS:
        op.execute(
            _complexe.update()
            .where(_where(ref))
            .values(
                grammage_g_m2=grammage,
                epaisseur_microns=epaisseur,
                est_transparent=transp,
                opacite_pct=opacite,
                sous_type=sous_type,
            )
        )
    for ref, sous_type in PAPIERS:
        op.execute(
            _complexe.update()
            .where(_where(ref))
            .values(
                epaisseur_microns=None,
                est_transparent=False,
                opacite_pct=95.0,
                sous_type=sous_type,
            )
        )


def downgrade() -> None:
    # Films : grammage remis à NULL (état antérieur au Lot 1).
    for ref, *_ in FILMS:
        op.execute(
            _complexe.update()
            .where(_where(ref))
            .values(
                grammage_g_m2=None,
                epaisseur_microns=None,
                est_transparent=False,
                opacite_pct=None,
                sous_type=None,
            )
        )
    # Papiers : grammage conservé ; champs techniques remis à NULL.
    for ref, _sous_type in PAPIERS:
        op.execute(
            _complexe.update()
            .where(_where(ref))
            .values(
                epaisseur_microns=None,
                est_transparent=False,
                opacite_pct=None,
                sous_type=None,
            )
        )
