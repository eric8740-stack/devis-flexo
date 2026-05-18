"""Tests du mapping rotation_se — convention métier flexographique officielle.

Verrouillé le 18/05/2026. Les paires extérieur/intérieur (1/5, 2/6, 3/7,
4/8) partagent les MÊMES rotations VUE A et VUE C : la différence est
purement la face imprimée, visible uniquement côté VUE B (image Canva).

PAS de logique miroir, PAS de règle "(VUE A + 90°) mod 360" — mappings
explicites verrouillés par Eric (28 ans XP flexo).
"""
import pytest

from app.services.rotation_se import (
    LIBELLES_OFFICIELS,
    ROTATION_VUE_A,
    ROTATION_VUE_C,
    get_libelle_officiel,
    get_rotation_vue_a,
    get_rotation_vue_c,
)


# ---------------------------------------------------------------------------
# VUE A — planche presse (sens machine, AVANCE vers le bas)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sens,attendu",
    [
        (1, 90),   # droite avant
        (2, 270),  # gauche avant
        (3, 0),    # pied avant
        (4, 180),  # tête avant
        (5, 90),
        (6, 270),
        (7, 0),
        (8, 180),
    ],
)
def test_rotation_vue_a_par_sens(sens, attendu):
    assert get_rotation_vue_a(sens) == attendu


# ---------------------------------------------------------------------------
# VUE C — bobine fille chez le client (défilement horizontal vers la droite)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sens,attendu",
    [
        (1, 0),    # droite avant → A debout (lecture normale)
        (2, 180),  # gauche avant → A renversé
        (3, 270),  # pied avant → A couché tête à gauche, pieds à droite
        (4, 90),   # tête avant → A couché tête à droite, pieds à gauche
        (5, 0),
        (6, 180),
        (7, 270),
        (8, 90),
    ],
)
def test_rotation_vue_c_par_sens(sens, attendu):
    assert get_rotation_vue_c(sens) == attendu


# ---------------------------------------------------------------------------
# Cohérence paires extérieur/intérieur (1/5, 2/6, 3/7, 4/8)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ext,interieur", [(1, 5), (2, 6), (3, 7), (4, 8)])
def test_paires_ext_int_meme_rotation_vue_a(ext, interieur):
    assert get_rotation_vue_a(ext) == get_rotation_vue_a(interieur)


@pytest.mark.parametrize("ext,interieur", [(1, 5), (2, 6), (3, 7), (4, 8)])
def test_paires_ext_int_meme_rotation_vue_c(ext, interieur):
    assert get_rotation_vue_c(ext) == get_rotation_vue_c(interieur)


@pytest.mark.parametrize("ext,interieur", [(1, 5), (2, 6), (3, 7), (4, 8)])
def test_paires_ext_int_libelles_diffèrent_uniquement_par_face(ext, interieur):
    """Les libellés ext/int sont identiques sauf le mot Extérieur/Intérieur."""
    lib_ext = get_libelle_officiel(ext)
    lib_int = get_libelle_officiel(interieur)
    assert "Extérieur" in lib_ext and "Intérieur" not in lib_ext
    assert "Intérieur" in lib_int and "Extérieur" not in lib_int
    assert lib_ext.replace("Extérieur", "Intérieur") == lib_int


# ---------------------------------------------------------------------------
# Libellés officiels (verrouillés, chaîne exacte attendue)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sens,libelle",
    [
        (1, "0° Extérieur droite avant"),
        (2, "180° Extérieur gauche avant"),
        (3, "270° Extérieur pied avant"),
        (4, "90° Extérieur tête avant"),
        (5, "0° Intérieur droite avant"),
        (6, "180° Intérieur gauche avant"),
        (7, "270° Intérieur pied avant"),
        (8, "90° Intérieur tête avant"),
    ],
)
def test_libelle_officiel_par_sens(sens, libelle):
    assert get_libelle_officiel(sens) == libelle


# ---------------------------------------------------------------------------
# Validation des bornes (sens invalide → ValueError)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sens_invalide", [0, 9, -1, 100])
def test_sens_invalide_rotation_vue_a(sens_invalide):
    with pytest.raises(ValueError):
        get_rotation_vue_a(sens_invalide)


@pytest.mark.parametrize("sens_invalide", [0, 9, -1, 100])
def test_sens_invalide_rotation_vue_c(sens_invalide):
    with pytest.raises(ValueError):
        get_rotation_vue_c(sens_invalide)


@pytest.mark.parametrize("sens_invalide", [0, 9, -1, 100])
def test_sens_invalide_libelle(sens_invalide):
    with pytest.raises(ValueError):
        get_libelle_officiel(sens_invalide)


# ---------------------------------------------------------------------------
# Sanity dicts complets (8 entrées par mapping)
# ---------------------------------------------------------------------------


def test_dicts_completness():
    assert set(ROTATION_VUE_A.keys()) == {1, 2, 3, 4, 5, 6, 7, 8}
    assert set(ROTATION_VUE_C.keys()) == {1, 2, 3, 4, 5, 6, 7, 8}
    assert set(LIBELLES_OFFICIELS.keys()) == {1, 2, 3, 4, 5, 6, 7, 8}
    # Toutes les rotations sont des multiples de 90 dans [0, 270]
    for v in list(ROTATION_VUE_A.values()) + list(ROTATION_VUE_C.values()):
        assert v in {0, 90, 180, 270}
