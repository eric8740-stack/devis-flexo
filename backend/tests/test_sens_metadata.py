"""Tests de la façade `sens_metadata` — couvre les 10 sens (0-9).

- Sens 1-8 : valeurs déléguées strictement à rotation_se (verrouillé).
- Sens 0 / 9 : bobines vierges (sans impression) — libellés dédiés,
  rotations à 0 (pas de cliché à orienter).

Le module `rotation_se` reste intact (verrouillé 18/05/2026, Eric — 28 ans
XP flexo) ; ses tests historiques continuent d'asserter qu'il refuse 0/9.
"""
import pytest

from app.services import rotation_se
from app.services.sens_metadata import (
    get_libelle_officiel,
    get_rotation_vue_a,
    get_rotation_vue_c,
    is_sens_vierge,
)


@pytest.mark.parametrize("sens", [0, 9])
def test_is_sens_vierge_true(sens):
    assert is_sens_vierge(sens) is True


@pytest.mark.parametrize("sens", [1, 2, 3, 4, 5, 6, 7, 8])
def test_is_sens_vierge_false_pour_1_8(sens):
    assert is_sens_vierge(sens) is False


# Sens 0 / 9 — libellés exacts (fournis au BAT et formulaire devis).
def test_libelle_sens_0_vierge_exterieur():
    assert get_libelle_officiel(0) == "0° Extérieur · sans impression"


def test_libelle_sens_9_vierge_interieur():
    assert get_libelle_officiel(9) == "0° Intérieur · sans impression"


# Sens 0 / 9 — rotations à 0 (pas de cliché → pas d'orientation).
@pytest.mark.parametrize("sens", [0, 9])
def test_rotation_vue_a_sens_vierge_zero(sens):
    assert get_rotation_vue_a(sens) == 0


@pytest.mark.parametrize("sens", [0, 9])
def test_rotation_vue_c_sens_vierge_zero(sens):
    assert get_rotation_vue_c(sens) == 0


# Sens 1-8 — délégation stricte à rotation_se : la façade doit renvoyer
# les MÊMES valeurs que le module verrouillé (équivalence comportementale).
@pytest.mark.parametrize("sens", [1, 2, 3, 4, 5, 6, 7, 8])
def test_delegation_libelle_pour_1_8(sens):
    assert get_libelle_officiel(sens) == rotation_se.get_libelle_officiel(sens)


@pytest.mark.parametrize("sens", [1, 2, 3, 4, 5, 6, 7, 8])
def test_delegation_rotation_vue_a_pour_1_8(sens):
    assert get_rotation_vue_a(sens) == rotation_se.get_rotation_vue_a(sens)


@pytest.mark.parametrize("sens", [1, 2, 3, 4, 5, 6, 7, 8])
def test_delegation_rotation_vue_c_pour_1_8(sens):
    assert get_rotation_vue_c(sens) == rotation_se.get_rotation_vue_c(sens)


# Hors plage 0-9 → toujours ValueError (via rotation_se pour les valeurs
# qui ne sont ni vierges ni dans 1-8).
@pytest.mark.parametrize("sens_invalide", [-1, 10, 100])
def test_sens_hors_plage_leve_value_error(sens_invalide):
    with pytest.raises(ValueError):
        get_libelle_officiel(sens_invalide)
    with pytest.raises(ValueError):
        get_rotation_vue_a(sens_invalide)
    with pytest.raises(ValueError):
        get_rotation_vue_c(sens_invalide)
