"""Tests règle compensation laize/dev Sprint 13 S13.D.3.

CdC § 531-554 : quand l'intervalle dev est forcément grand (cylindre non
idéal), le squelette devient fragile DANS LE SENS DU DÉROULÉ. Pour
consolider, on peut élargir l'intervalle laize (entre colonnes) afin
d'avoir plus de matière transverse.

Barème ICE :
  dev ≤ 4 mm   : aucun bonus nécessaire (déjà optimal)
  dev = 5 mm   : laize ≥ 4 mm → coef vitesse 0.70 → 0.85
  dev = 6 mm   : laize ≥ 5 mm → coef vitesse 0.60 → 0.80
  dev 7-8 mm   : laize ≥ 6 mm → coef vitesse 0.50 → 0.70
  dev > 8 mm   : laize ≥ 70 % du dev → coef vitesse 0.40 → 0.60

Note CdC § 702 : intervalle laize MAX = 5 mm (limite pratique). Au-delà
= matière perdue. La consolidation à 6 mm sur dev 7-8 et à 70% sur dev>8
sont des cas EDGE rarement atteints en pratique.
"""
import pytest

from app.data.catalogue_defaults import get_bareme_by_code
from app.services.optimisation.regles.compensation_laize_dev import (
    evaluer_compensation,
    lookup_palier_compensation,
)


BAREME_ICE = get_bareme_by_code("compensation_laize_dev_ice")["bareme_data"]


# ---------------------------------------------------------------------------
# lookup_palier_compensation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "intervalle_dev_mm,laize_souhaitable_attendue,coef_attendu",
    [
        (2.0, 3, None),    # palier 0-4 : pas de bonus
        (3.0, 3, None),
        (4.0, 3, None),
        (4.5, 4, 0.85),    # palier 4-5
        (5.0, 4, 0.85),
        (5.5, 5, 0.80),    # palier 5-6
        (6.0, 5, 0.80),
        (7.0, 6, 0.70),    # palier 6-8
        (8.0, 6, 0.70),
        # > 8 → palier "70% du dev" sans intervalle_laize_souhaitable_mm fixe
    ],
)
def test_lookup_palier_paliers_fixes(
    intervalle_dev_mm, laize_souhaitable_attendue, coef_attendu
):
    palier = lookup_palier_compensation(intervalle_dev_mm, BAREME_ICE)
    assert palier["intervalle_laize_souhaitable_mm"] == laize_souhaitable_attendue
    assert palier["coef_vitesse_si_atteint"] == coef_attendu


def test_lookup_palier_au_dela_de_8_renvoie_palier_pct():
    """> 8 mm : palier dynamique 70 % du dev, pas de seuil mm fixe."""
    palier = lookup_palier_compensation(10.0, BAREME_ICE)
    assert palier.get("intervalle_laize_souhaitable_pct_dev") == 70
    assert palier["coef_vitesse_si_atteint"] == 0.60


def test_lookup_palier_bareme_vide_retourne_neutre():
    palier = lookup_palier_compensation(5.0, [])
    assert palier["coef_vitesse_si_atteint"] is None
    assert palier["intervalle_laize_souhaitable_mm"] is None


# ---------------------------------------------------------------------------
# evaluer_compensation
# ---------------------------------------------------------------------------


def test_dev_optimal_pas_de_consolidation_necessaire():
    """dev ≤ 4 mm : consolidation_atteinte = False mais c'est OK (pas
    de bonus a appliqué de toute façon)."""
    res = evaluer_compensation(
        intervalle_dev_mm=3.0, intervalle_laize_mm=2.0, bareme=BAREME_ICE
    )
    assert res["consolidation_atteinte"] is False
    assert res["coef_vitesse_si_atteint"] is None
    assert res["intervalle_laize_souhaitable_mm"] == 3


def test_dev_5mm_laize_4_consolidation_atteinte():
    """dev 5 mm + laize 4 mm exactement → consolidation atteinte,
    coef passe de 0.70 à 0.85."""
    res = evaluer_compensation(
        intervalle_dev_mm=5.0, intervalle_laize_mm=4.0, bareme=BAREME_ICE
    )
    assert res["consolidation_atteinte"] is True
    assert res["coef_vitesse_si_atteint"] == 0.85


def test_dev_5mm_laize_3_consolidation_non_atteinte():
    """dev 5 mm + laize 3 mm < 4 mm → consolidation non atteinte,
    on subit 0.70 du palier echenillage standard."""
    res = evaluer_compensation(
        intervalle_dev_mm=5.0, intervalle_laize_mm=3.0, bareme=BAREME_ICE
    )
    assert res["consolidation_atteinte"] is False
    assert res["coef_vitesse_si_atteint"] is None
    assert res["intervalle_laize_souhaitable_mm"] == 4


def test_dev_6mm_laize_5_consolidation_atteinte():
    res = evaluer_compensation(
        intervalle_dev_mm=6.0, intervalle_laize_mm=5.0, bareme=BAREME_ICE
    )
    assert res["consolidation_atteinte"] is True
    assert res["coef_vitesse_si_atteint"] == 0.80


def test_dev_10mm_palier_pct_seuil_dynamique():
    """dev 10 mm : seuil laize = 70 % × 10 = 7 mm. Laize 7 mm exactement
    → consolidation atteinte, coef 0.60.
    (En pratique impossible car laize max 5 mm CdC § 702, mais on teste
    le calcul théorique.)
    """
    res = evaluer_compensation(
        intervalle_dev_mm=10.0, intervalle_laize_mm=7.0, bareme=BAREME_ICE
    )
    assert res["consolidation_atteinte"] is True
    assert res["coef_vitesse_si_atteint"] == 0.60


def test_dev_10mm_laize_6_non_atteinte():
    """dev 10 mm : seuil = 70 % × 10 = 7 mm. Laize 6 < 7 → non atteint."""
    res = evaluer_compensation(
        intervalle_dev_mm=10.0, intervalle_laize_mm=6.0, bareme=BAREME_ICE
    )
    assert res["consolidation_atteinte"] is False
    assert res["coef_vitesse_si_atteint"] is None
    assert res["intervalle_laize_souhaitable_mm"] == 7.0  # 70% de 10
