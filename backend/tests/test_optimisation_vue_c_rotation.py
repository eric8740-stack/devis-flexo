"""Tests rotation A pour les vues BAT (mapping SE → degrés).

Vérifie le mapping ROTATION_VUE_A + ROTATION_VUE_C de
`app.services.optimisation.rotation_se`. Les paires extérieur/intérieur
(1/5, 2/6, 3/7, 4/8) partagent la même rotation — seule la face diffère
(visible VUE B image bobine).
"""
import pytest

from app.services.optimisation.rotation_se import (
    rotation_vue_a_deg,
    rotation_vue_c_deg,
)


# ---------------------------------------------------------------------------
# VUE C — bobine fille chez le client (sens horizontal, client final)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sens,rotation_attendue",
    [
        ("SE1", 0),    # droite avant → A debout
        ("SE2", 180),  # gauche avant → A renversé
        ("SE3", 90),   # pied avant   → A tête à gauche (90°)
        ("SE4", 270),  # tête avant   → A tête à droite (270°)
        ("SE5", 0),    # idem SE1 (face int, même rotation)
        ("SE6", 180),
        ("SE7", 90),
        ("SE8", 270),
    ],
)
def test_rotation_vue_c_par_sens(sens, rotation_attendue):
    assert rotation_vue_c_deg(sens) == rotation_attendue


def test_paires_ext_int_meme_rotation_vue_c():
    """Les sens 1/5, 2/6, 3/7, 4/8 partagent la même rotation VUE C."""
    assert rotation_vue_c_deg("SE1") == rotation_vue_c_deg("SE5")
    assert rotation_vue_c_deg("SE2") == rotation_vue_c_deg("SE6")
    assert rotation_vue_c_deg("SE3") == rotation_vue_c_deg("SE7")
    assert rotation_vue_c_deg("SE4") == rotation_vue_c_deg("SE8")


# ---------------------------------------------------------------------------
# VUE A — plaque sens machine (déjà corrigée PR #16, smoke check)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sens,rotation_attendue",
    [
        ("SE1", 270),  # droite avant
        ("SE2", 90),   # gauche avant
        ("SE3", 0),    # pied avant
        ("SE4", 180),  # tête avant
        ("SE5", 270),
        ("SE6", 90),
        ("SE7", 0),
        ("SE8", 180),
    ],
)
def test_rotation_vue_a_par_sens(sens, rotation_attendue):
    assert rotation_vue_a_deg(sens) == rotation_attendue


def test_paires_ext_int_meme_rotation_vue_a():
    """Idem pour VUE A : seule la face diffère."""
    assert rotation_vue_a_deg("SE1") == rotation_vue_a_deg("SE5")
    assert rotation_vue_a_deg("SE2") == rotation_vue_a_deg("SE6")
    assert rotation_vue_a_deg("SE3") == rotation_vue_a_deg("SE7")
    assert rotation_vue_a_deg("SE4") == rotation_vue_a_deg("SE8")


# ---------------------------------------------------------------------------
# Cohérence VUE A vs VUE C : la VUE C est décalée de +90° par rapport à VUE A
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sens", ["SE1", "SE2", "SE3", "SE4", "SE5", "SE6", "SE7", "SE8"])
def test_vue_c_egal_vue_a_plus_90_modulo_360(sens):
    """La VUE C tourne le A de +90° par rapport à VUE A (changement de
    référentiel : sens machine vertical → sens client horizontal)."""
    attendu = (rotation_vue_a_deg(sens) + 90) % 360
    assert rotation_vue_c_deg(sens) == attendu
