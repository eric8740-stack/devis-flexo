"""Tests fonctions BAT — PR #9.1.

Cas métier de référence Eric : étiquette laize 100 × dev 80 mm, 4×2=8
poses sur cylindre 104 dents (330.2 mm), intervalle_laize 5 mm,
chute_min 10 mm, palier 10 mm, marge_liner 2.5 mm.
"""
import pytest

from app.services.optimisation.bat_calculs import (
    calcul_chute_reelle_par_cote,
    calcul_diametre_bobine,
    calcul_laize_liner,
    calcul_laize_papier,
    calcul_laize_plaque,
    calcul_m2_consomme,
    calcul_ml_total,
    calcul_rendement,
)


# ---------------------------------------------------------------------------
# Cas Eric 100×80, 4×2 sur cyl 104 dents
# ---------------------------------------------------------------------------


def test_calcul_laize_plaque_2_poses_100mm_intervalle_5():
    """2 poses 100 mm + 1 intervalle 5 mm = 205 mm de plaque."""
    assert calcul_laize_plaque(2, 100.0, 5.0) == 205.0


def test_calcul_laize_papier_arrondi_au_palier_superieur():
    """Plaque 205 + 2×chute 10 = 225 mini, arrondi palier 10 → 230 mm."""
    assert calcul_laize_papier(205.0, 10.0, 10) == 230


def test_calcul_chute_reelle_symetrique():
    """Papier 230, plaque 205 → 12.5 mm de chute de chaque côté."""
    assert calcul_chute_reelle_par_cote(230.0, 205.0) == 12.5


def test_calcul_ml_total_cas_eric_quantite_pile():
    """10000 étiq / (4×2 poses) = 1250 tours pile × cyl 330.2 mm /1000
    = 412.75 m."""
    assert calcul_ml_total(10_000, 4, 2, 330.2) == pytest.approx(412.75, abs=0.01)


def test_calcul_m2_consomme_412_x_230():
    """412.75 m × 230 mm = 94.93 m²."""
    assert calcul_m2_consomme(412.75, 230) == pytest.approx(94.9325, abs=0.001)


def test_calcul_rendement_cas_eric():
    """10000 × 100×80 mm² = 80 m² utiles. 80 / 94.93 ≈ 84.27 %."""
    rdt = calcul_rendement(10_000, 100.0, 80.0, 94.9325)
    assert rdt == pytest.approx(84.27, abs=0.05)


def test_calcul_diametre_bobine_velin_145um_mandrin_76():
    """Estimation ø bobine pour le cas Eric (ml=412.75, épais 145µm,
    mandrin 76, laize 230). Le calcul exact basé sur la formule
    volumique donne ≈ 278 mm."""
    diam = calcul_diametre_bobine(412.75, 145.0, 76, 230.0)
    # Tolérance large (modèle volumique sans air entre couches)
    assert 250 <= diam <= 310, f"diam={diam} hors plage attendue"


def test_calcul_laize_liner_etiq_100_marge_2_5():
    """Étiq 100 + 2× 2.5 = 105 mm de liner."""
    assert calcul_laize_liner(100.0, 2.5) == 105.0


# ---------------------------------------------------------------------------
# Edge cases & garde-fous
# ---------------------------------------------------------------------------


def test_calcul_ml_total_arrondi_ceil_tour_entame():
    """Convention métier : tour entamé = tour fini. 10001 / 8 = 1250.125
    → ceil 1251 tours → ml = 1251 × 330.2 / 1000 = 413.08 m."""
    ml = calcul_ml_total(10_001, 4, 2, 330.2)
    assert ml == pytest.approx(413.08, abs=0.01)


def test_calcul_laize_papier_palier_5_au_lieu_de_10():
    """Si tenant change palier à 5 (papier livré au 5 mm près), 225 mini
    → arrondi 225 (déjà multiple de 5) → 225 mm."""
    assert calcul_laize_papier(205.0, 10.0, 5) == 225


def test_calcul_laize_papier_chute_15_au_lieu_de_10():
    """Si tenant met chute_min 15 → 205 + 30 = 235 mini → palier 10 → 240."""
    assert calcul_laize_papier(205.0, 15.0, 10) == 240


def test_calcul_laize_papier_palier_zero_leve_value_error():
    with pytest.raises(ValueError):
        calcul_laize_papier(205.0, 10.0, 0)


def test_sanity_laize_papier_toujours_superieure_plaque_plus_chute():
    """Pour toute config raisonnable, laize_papier ≥ plaque + 2×chute_min."""
    for plaque in [100, 150, 205, 280, 320]:
        for chute in [5, 10, 12.5, 15]:
            for palier in [5, 10, 25]:
                papier = calcul_laize_papier(plaque, chute, palier)
                assert papier >= plaque + 2 * chute, (
                    f"plaque={plaque} chute={chute} palier={palier} "
                    f"→ papier={papier} mais devrait être ≥ {plaque + 2 * chute}"
                )


def test_calcul_rendement_zero_si_m2_consomme_nul():
    assert calcul_rendement(10_000, 100, 80, 0) == 0.0


def test_calcul_ml_total_poses_zero_renvoie_zero():
    """Cas dégénéré (config impossible) : ne plante pas, renvoie 0."""
    assert calcul_ml_total(10_000, 0, 2, 330.2) == 0.0
    assert calcul_ml_total(10_000, 4, 0, 330.2) == 0.0
