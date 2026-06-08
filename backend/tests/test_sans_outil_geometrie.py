"""Lot back A — géométrie pure « mode sans outil » (impression pleine largeur + refente).

Tests unitaires sans DB du helper `calculer_geometrie_sans_outil` :
nb filles de refente, déchet latéral (stock − utile), ml cylinder-free,
plafond laize imprimable (min stock/presse).
"""
import math

import pytest

from app.services.optimisation.sans_outil import (
    GeometrieSansOutil,
    calculer_geometrie_sans_outil,
)


def test_nb_filles_et_dechet_lateral_nominal():
    """Stock 220, format 50, intervalle 3, presse large : 4 filles.
    pas = 53 ; (220+3)/53 = 4.20 → 4 filles.
    utile = 4×50 + 3×3 = 209 ; déchet = 220 − 209 = 11.
    """
    g = calculer_geometrie_sans_outil(
        laize_stock_mm=220.0,
        laize_utile_presse_mm=330.0,
        format_largeur_mm=50.0,
        format_hauteur_mm=40.0,
        intervalle_laize_mm=3.0,
        quantite=10_000,
    )
    assert isinstance(g, GeometrieSansOutil)
    assert g.nb_filles == 4
    assert g.laize_imprimable_mm == 220.0
    assert g.laize_utile_refente_mm == pytest.approx(209.0)
    assert g.dechet_lateral_mm == pytest.approx(11.0)


def test_ml_total_cylinder_free():
    """ml = ceil(quantite × hauteur / (nb_filles × 1000)).
    4 filles, hauteur 40, qté 10 000 → 10000×40/(4×1000)=100 m."""
    g = calculer_geometrie_sans_outil(
        220.0, 330.0, 50.0, 40.0, 3.0, 10_000
    )
    assert g.ml_total == pytest.approx(100.0)


def test_plafond_laize_imprimable_min_stock_presse():
    """Si la presse est plus étroite que la bobine stock, on imprime la
    laize presse — mais le déchet reste calculé sur le STOCK facturé."""
    g = calculer_geometrie_sans_outil(
        laize_stock_mm=400.0,
        laize_utile_presse_mm=330.0,
        format_largeur_mm=100.0,
        format_hauteur_mm=80.0,
        intervalle_laize_mm=5.0,
        quantite=5_000,
    )
    # imprimable = min(400, 330) = 330 ; pas=105 ; (330+5)/105=3.19 → 3 filles.
    assert g.laize_imprimable_mm == 330.0
    assert g.nb_filles == 3
    # utile = 3×100 + 2×5 = 310 ; déchet sur stock 400 → 90.
    assert g.laize_utile_refente_mm == pytest.approx(310.0)
    assert g.dechet_lateral_mm == pytest.approx(90.0)


def test_intervalle_laize_zero_colle_les_filles():
    """intervalle_laize = 0 → filles jointives, déchet = stock − n×largeur."""
    g = calculer_geometrie_sans_outil(
        200.0, 330.0, 50.0, 30.0, 0.0, 1_000
    )
    assert g.nb_filles == 4  # floor(200/50)
    assert g.laize_utile_refente_mm == pytest.approx(200.0)
    assert g.dechet_lateral_mm == pytest.approx(0.0)


def test_format_trop_large_retourne_none():
    """Format plus large que la laize imprimable → aucune fille → None."""
    g = calculer_geometrie_sans_outil(
        100.0, 100.0, 150.0, 40.0, 2.0, 1_000
    )
    assert g is None


def test_dechet_jamais_negatif():
    """Le déchet est planché à 0 (jamais négatif même si arrondis serrés)."""
    g = calculer_geometrie_sans_outil(
        150.0, 150.0, 50.0, 30.0, 0.0, 1_000
    )
    assert g is not None
    assert g.dechet_lateral_mm >= 0.0


def test_format_invalide_leve_valueerror():
    with pytest.raises(ValueError):
        calculer_geometrie_sans_outil(220.0, 330.0, 0.0, 40.0, 3.0, 1_000)
    with pytest.raises(ValueError):
        calculer_geometrie_sans_outil(220.0, 330.0, 50.0, 40.0, -1.0, 1_000)


# ---------------------------------------------------------------------------
# Override nb_filles (souveraineté opérateur)
# ---------------------------------------------------------------------------


def test_nb_filles_force_une_seule_fille():
    """Force 1 fille (pas de refente / pistes regroupées) : utile = largeur,
    déchet = stock − largeur, ml recalculé sur 1 fille."""
    g = calculer_geometrie_sans_outil(
        laize_stock_mm=220.0,
        laize_utile_presse_mm=330.0,
        format_largeur_mm=50.0,
        format_hauteur_mm=40.0,
        intervalle_laize_mm=3.0,
        quantite=10_000,
        nb_filles_force=1,
    )
    assert g is not None
    assert g.nb_filles == 1
    assert g.laize_utile_refente_mm == pytest.approx(50.0)
    assert g.dechet_lateral_mm == pytest.approx(170.0)
    # ml = ceil(10000×40 / (1×1000)) = 400.
    assert g.ml_total == pytest.approx(400.0)


def test_nb_filles_force_infaisable_retourne_none():
    """Forcer plus de filles que la laize imprimable ne permet → None."""
    # dérivé = 4 filles ; forcer 10 → utile 10×50+9×3 = 527 > 220 → None.
    g = calculer_geometrie_sans_outil(
        220.0, 330.0, 50.0, 40.0, 3.0, 10_000, nb_filles_force=10
    )
    assert g is None


def test_nb_filles_force_egal_derive_inchange():
    """Forcer la valeur dérivée ne change rien (comportement inchangé)."""
    base = calculer_geometrie_sans_outil(220.0, 330.0, 50.0, 40.0, 3.0, 10_000)
    forced = calculer_geometrie_sans_outil(
        220.0, 330.0, 50.0, 40.0, 3.0, 10_000, nb_filles_force=base.nb_filles
    )
    assert forced == base


def test_nb_filles_force_zero_leve_valueerror():
    with pytest.raises(ValueError):
        calculer_geometrie_sans_outil(
            220.0, 330.0, 50.0, 40.0, 3.0, 1_000, nb_filles_force=0
        )
