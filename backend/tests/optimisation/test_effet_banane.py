"""Tests règle effet banane Sprint 13 S13.D.1 (filtre dur).

CdC § 556-581 : plus la plaque est large, plus le développé cylindre
minimum requis est grand. Filtre dur — un cylindre exclu est définitivement
exclu, pas de compromis.

Barème ICE par défaut (CdC ligne 571) — valeurs en mm réels après fix
Cas B du 2026-05-16 (×3.175 sur les anciennes valeurs "dents") :
  ≤ 150 mm  → Z mini 254 mm  (80 dents)
  150-200   → Z mini 304.8   (96 dents)
  200-250   → Z mini 330.2   (104 dents)
  250-300   → Z mini 381     (120 dents)
  300-350   → Z mini 508     (160 dents — saut non-linéaire, seuil physique)
  > 350     → Z mini 508
"""
import pytest

from app.data.catalogue_defaults import get_bareme_by_code
from app.services.optimisation.regles.effet_banane import (
    lookup_developpe_mini,
    valide_effet_banane,
)
from app.services.optimisation.types import Cylindre


BAREME_ICE = get_bareme_by_code("effet_banane_ice")["bareme_data"]


# ---------------------------------------------------------------------------
# lookup_developpe_mini
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "largeur_mm,z_attendu",
    [
        (50, 254.0),       # très étroit
        (149.9, 254.0),    # juste sous palier 150
        (150, 254.0),      # pile au seuil 150 → encore palier ≤ 150
        (150.01, 304.8),   # juste au-dessus → bascule sur palier 200
        (180, 304.8),      # plein milieu palier 200
        (200, 304.8),      # pile seuil 200
        (200.01, 330.2),
        (250, 330.2),
        (250.01, 381.0),
        (300, 381.0),
        (300.01, 508.0),   # SAUT NON-LINÉAIRE 381 → 508
        (350, 508.0),
        (400, 508.0),
        (999, 508.0),      # au-delà : reste 508
    ],
)
def test_lookup_developpe_mini_paliers(largeur_mm, z_attendu):
    assert lookup_developpe_mini(largeur_mm, BAREME_ICE) == z_attendu


# ---------------------------------------------------------------------------
# valide_effet_banane
# ---------------------------------------------------------------------------


def test_valide_cylindre_assez_grand_pour_plaque_etroite():
    cyl = Cylindre(id=1, developpe_mm=304.8)  # 96 dents
    res = valide_effet_banane(cyl, largeur_plaque_mm=100, bareme=BAREME_ICE)
    assert res.ok is True
    assert res.raison is None


def test_exclu_cylindre_trop_petit_pour_plaque_large():
    """Plaque 300 mm → Z mini 381 (120 dents). Cylindre 304.8 (96 dents) → EXCLU."""
    cyl = Cylindre(id=1, developpe_mm=304.8)
    res = valide_effet_banane(cyl, largeur_plaque_mm=300, bareme=BAREME_ICE)
    assert res.ok is False
    assert res.raison == "effet_banane"
    assert "304.8" in res.message
    assert "381" in res.message


def test_pile_au_seuil_z_mini_egal_developpe_ok():
    """Z mini requis = développé → OK (pas une exclusion stricte)."""
    cyl = Cylindre(id=1, developpe_mm=304.8)  # 96 dents
    res = valide_effet_banane(cyl, largeur_plaque_mm=200, bareme=BAREME_ICE)
    assert res.ok is True


def test_saut_non_lineaire_300_350_bien_applique():
    """Plaque 301 mm → Z mini 508 mm (pas 381). Cyl 457.2 (144 dents) → EXCLU."""
    cyl = Cylindre(id=1, developpe_mm=457.2)
    res = valide_effet_banane(cyl, largeur_plaque_mm=301, bareme=BAREME_ICE)
    assert res.ok is False
    assert res.raison == "effet_banane"


def test_grand_cylindre_passe_toujours():
    cyl = Cylindre(id=1, developpe_mm=508.0)  # 160 dents = Z mini max requis
    for largeur in [50, 200, 350, 500]:
        res = valide_effet_banane(cyl, largeur_plaque_mm=largeur, bareme=BAREME_ICE)
        assert res.ok, f"Cyl 508 devrait passer largeur={largeur}"


def test_bareme_vide_ne_filtre_rien():
    """Si l'imprimerie n'a pas configuré de barème (cas edge), on laisse
    passer (pas de Z mini imposé)."""
    cyl = Cylindre(id=1, developpe_mm=228.6)  # 72 dents
    res = valide_effet_banane(cyl, largeur_plaque_mm=400, bareme=[])
    assert res.ok is True
