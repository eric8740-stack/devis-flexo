"""Tests règle effet banane Sprint 13 S13.D.1 (filtre dur).

CdC § 556-581 : plus la plaque est large, plus le développé cylindre
minimum requis est grand. Filtre dur — un cylindre exclu est définitivement
exclu, pas de compromis.

Barème ICE par défaut (CdC ligne 571) :
  ≤ 150 mm → Z mini 80 mm
  150-200 → Z mini 96
  200-250 → Z mini 104
  250-300 → Z mini 120
  300-350 → Z mini 160  (saut non-linéaire, seuil physique)
  > 350   → Z mini 160
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
        (50, 80),       # très étroit
        (149.9, 80),    # juste sous palier 150
        (150, 80),      # pile au seuil 150 → encore palier ≤ 150
        (150.01, 96),   # juste au-dessus → bascule sur palier 200
        (180, 96),      # plein milieu palier 200
        (200, 96),      # pile seuil 200
        (200.01, 104),
        (250, 104),
        (250.01, 120),
        (300, 120),
        (300.01, 160),  # SAUT NON-LINÉAIRE 120 → 160
        (350, 160),
        (400, 160),
        (999, 160),     # au-delà : reste 160
    ],
)
def test_lookup_developpe_mini_paliers(largeur_mm, z_attendu):
    assert lookup_developpe_mini(largeur_mm, BAREME_ICE) == z_attendu


# ---------------------------------------------------------------------------
# valide_effet_banane
# ---------------------------------------------------------------------------


def test_valide_cylindre_assez_grand_pour_plaque_etroite():
    cyl = Cylindre(id=1, developpe_mm=96)
    res = valide_effet_banane(cyl, largeur_plaque_mm=100, bareme=BAREME_ICE)
    assert res.ok is True
    assert res.raison is None


def test_exclu_cylindre_trop_petit_pour_plaque_large():
    """Plaque 300 mm → Z mini 120. Cylindre 96 → EXCLU."""
    cyl = Cylindre(id=1, developpe_mm=96)
    res = valide_effet_banane(cyl, largeur_plaque_mm=300, bareme=BAREME_ICE)
    assert res.ok is False
    assert res.raison == "effet_banane"
    assert "96" in res.message
    assert "120" in res.message


def test_pile_au_seuil_z_mini_egal_developpe_ok():
    """Z mini requis = développé → OK (pas une exclusion stricte)."""
    cyl = Cylindre(id=1, developpe_mm=96)
    res = valide_effet_banane(cyl, largeur_plaque_mm=200, bareme=BAREME_ICE)
    assert res.ok is True


def test_saut_non_lineaire_300_350_bien_applique():
    """Plaque 301 mm → Z mini 160 (pas 120). Cylindre 144 → EXCLU."""
    cyl = Cylindre(id=1, developpe_mm=144)
    res = valide_effet_banane(cyl, largeur_plaque_mm=301, bareme=BAREME_ICE)
    assert res.ok is False
    assert res.raison == "effet_banane"


def test_grand_cylindre_passe_toujours():
    cyl = Cylindre(id=1, developpe_mm=160)
    # Cylindre 160 = Z mini max requis → passe partout y compris plaque large
    for largeur in [50, 200, 350, 500]:
        res = valide_effet_banane(cyl, largeur_plaque_mm=largeur, bareme=BAREME_ICE)
        assert res.ok, f"Cyl 160 devrait passer largeur={largeur}"


def test_bareme_vide_ne_filtre_rien():
    """Si l'imprimerie n'a pas configuré de barème (cas edge), on laisse
    passer (pas de Z mini imposé)."""
    cyl = Cylindre(id=1, developpe_mm=72)
    res = valide_effet_banane(cyl, largeur_plaque_mm=400, bareme=[])
    assert res.ok is True
