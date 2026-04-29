"""Tests unitaires du matcher cylindres magnétiques (S7 Lot 7d V2).

Formule corrigée : pas_mm = (Z × 3.175) / nb_etiq_par_tour
Plage Z=51..144, nb_etiq=1..40, intervalle 2.5-15, marge laize 5 mm.
"""
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.models import Machine
from app.services.cost_engine.cylindre_matcher import (
    DENT_MM,
    INTERVALLE_MAX,
    INTERVALLE_MIN,
    MARGE_SECURITE_LAIZE_MM,
    NB_ETIQ_MAX,
    NB_ETIQ_MIN,
    Z_MAX,
    Z_MIN,
    find_cylindre_candidats,
    lookup_z_mini_banane,
)
from app.services.cost_engine.errors import CostEngineError


# ---------------------------------------------------------------------------
# Constantes — garde-fous Sprint 7 V2
# ---------------------------------------------------------------------------


def test_constantes_plage_z_51_144():
    """V2 : plage Z corrigée 51-144 (vs 72-187 v1 abandonnée)."""
    assert Z_MIN == 51
    assert Z_MAX == 144


def test_constantes_plage_nb_etiq_1_40():
    """V2 : nb_etiq_par_tour 1-40 (limite haute tableau Develop.xlsx Eric)."""
    assert NB_ETIQ_MIN == 1
    assert NB_ETIQ_MAX == 40


def test_constante_dent_mm_un_huitieme_pouce():
    """1 dent = 1/8 pouce = 3.175 mm exactement."""
    assert DENT_MM == Decimal("3.175")


def test_constante_intervalle_borne_metier_25_15():
    assert INTERVALLE_MIN == Decimal("2.5")
    assert INTERVALLE_MAX == Decimal("15.0")


def test_constante_marge_securite_laize_5mm():
    """Décision Eric Q2 — défaut conservateur 5 mm chaque bord."""
    assert MARGE_SECURITE_LAIZE_MM == Decimal("5")


# ---------------------------------------------------------------------------
# lookup_z_mini_banane — table empirique 6 paliers + boundary tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "largeur_plaque, z_attendu",
    [
        (Decimal("100"), 80),    # palier ≤ 150
        (Decimal("149"), 80),
        (Decimal("150"), 80),    # ≤ 150 (incluse)
        (Decimal("151"), 96),    # > 150
        (Decimal("199"), 96),
        (Decimal("200"), 96),    # ≤ 200 (incluse)
        (Decimal("201"), 104),   # > 200
        (Decimal("249"), 104),
        (Decimal("250"), 104),   # ≤ 250 (incluse)
        (Decimal("251"), 120),   # > 250
        (Decimal("299"), 120),
        (Decimal("300"), 120),   # ≤ 300 (incluse)
        (Decimal("301"), 160),   # saut non-linéaire 120 → 160
        (Decimal("349"), 160),
        (Decimal("350"), 160),   # ≤ 350 (incluse)
        (Decimal("351"), 160),   # > 350 → 160 (palier max)
        (Decimal("500"), 160),   # cas extrême
    ],
)
def test_lookup_z_mini_banane_paliers(largeur_plaque, z_attendu):
    assert lookup_z_mini_banane(largeur_plaque) == z_attendu


# ---------------------------------------------------------------------------
# Sondes de validation formule (tableau Develop.xlsx Eric, section 10 brief)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "z, nb_etiq, pas_attendu",
    [
        (72, 5, Decimal("45.72")),     # 72 × 3.175 / 5 = 45.72
        (80, 5, Decimal("50.80")),     # 80 × 3.175 / 5 = 50.80
        (100, 3, Decimal("105.83")),   # 100 × 3.175 / 3 = 105.8333... ≈ 105.83
        (136, 3, Decimal("143.93")),   # 136 × 3.175 / 3 = 143.9333... ≈ 143.93
        (144, 4, Decimal("114.30")),   # 144 × 3.175 / 4 = 114.30
        (51, 5, Decimal("32.385")),    # 51 × 3.175 / 5 = 32.385
    ],
)
def test_formule_pas_correcte(z, nb_etiq, pas_attendu):
    """Sondes Develop.xlsx Eric — formule pas_mm = (Z × DENT_MM) / nb_etiq."""
    pas_calcule = (Decimal(z) * DENT_MM) / Decimal(nb_etiq)
    # Tolérance 0.01 mm pour les divisions non exactes (105.8333 vs 105.83)
    assert abs(pas_calcule - pas_attendu) <= Decimal("0.01"), (
        f"Z={z}, nb_etiq={nb_etiq} : pas calculé {pas_calcule} ≠ attendu {pas_attendu}"
    )


# ---------------------------------------------------------------------------
# find_cylindre_candidats — algorithme principal V2
# ---------------------------------------------------------------------------


def _machine_mark_andy() -> Machine:
    """Mark Andy P5 seedée (id=1, laize_max_mm=330)."""
    with SessionLocal() as db:
        return db.get(Machine, 1)


def test_find_candidats_v1a_format_40_largeur_180_top_3():
    """V1a-like : format_h=40, largeur=60×3=180. Plusieurs Z compatibles → top 3."""
    machine = _machine_mark_andy()
    candidats = find_cylindre_candidats(
        format_h_mm=40, largeur_plaque_mm=Decimal("180"), machine=machine
    )
    assert 1 <= len(candidats) <= 3
    for c in candidats:
        assert c.z >= 96, f"Z={c.z} < 96 (banane mini pour largeur 180)"
        assert NB_ETIQ_MIN <= c.nb_etiq_par_tour <= NB_ETIQ_MAX
        assert INTERVALLE_MIN <= c.intervalle_mm <= INTERVALLE_MAX
        # Cohérence formule
        attendu_circonf = Decimal(c.z) * DENT_MM
        assert c.circonference_mm == attendu_circonf
        attendu_pas = attendu_circonf / Decimal(c.nb_etiq_par_tour)
        assert c.pas_mm == attendu_pas
        assert c.intervalle_mm == attendu_pas - Decimal(40)
    # Tri intervalle croissant
    intervalles = [c.intervalle_mm for c in candidats]
    assert intervalles == sorted(intervalles)


def test_find_candidats_un_candidat_par_z():
    """Garde-fou : 1 candidat par Z (meilleur intervalle pour ce cylindre)."""
    machine = _machine_mark_andy()
    candidats = find_cylindre_candidats(
        format_h_mm=40, largeur_plaque_mm=Decimal("180"), machine=machine
    )
    z_set = {c.z for c in candidats}
    assert len(z_set) == len(candidats), "Doublons Z détectés (1 candidat / Z attendu)"


def test_find_candidats_largeur_excede_laize_machine():
    """Plaque 325 mm > laize 330 - 2×5 = 320 mm → CostEngineError."""
    machine = _machine_mark_andy()
    with pytest.raises(CostEngineError, match="laize"):
        find_cylindre_candidats(
            format_h_mm=40, largeur_plaque_mm=Decimal("325"), machine=machine
        )


def test_find_candidats_marge_admissible_exacte_320():
    """Plaque pile à laize - 2×marge = 320 mm → OK (≤ admissible).
    Note : largeur 320 → banane Z_mini=160 > Z_MAX=144 → 0 candidats → 422."""
    machine = _machine_mark_andy()
    with pytest.raises(CostEngineError, match="Aucun cylindre"):
        find_cylindre_candidats(
            format_h_mm=40, largeur_plaque_mm=Decimal("320"), machine=machine
        )


def test_find_candidats_largeur_180_laize_petite():
    """Plaque 180 sur Daco D250 (laize 250) : OK car 180 ≤ 250-10=240."""
    with SessionLocal() as db:
        daco = db.get(Machine, 2)  # Daco D250
    candidats = find_cylindre_candidats(
        format_h_mm=40, largeur_plaque_mm=Decimal("180"), machine=daco
    )
    assert len(candidats) >= 1


def test_find_candidats_aucun_format_extreme():
    """format_h trop grand → impossible avec plage Z 51-144 et intervalle ≤ 15."""
    machine = _machine_mark_andy()
    # Z_MAX=144, circonf max = 457.20, intervalle max = 15
    # → format_h_max = 457.20 - 15 = 442.20 mm
    # → format_h=600 → aucun (Z, nb_etiq) ne donne intervalle ∈ [2.5, 15]
    with pytest.raises(CostEngineError, match="Aucun cylindre"):
        find_cylindre_candidats(
            format_h_mm=600, largeur_plaque_mm=Decimal("100"), machine=machine
        )


def test_find_candidats_format_micro():
    """format_h=1, plage nb_etiq permet de trouver des candidats compatibles."""
    machine = _machine_mark_andy()
    candidats = find_cylindre_candidats(
        format_h_mm=1, largeur_plaque_mm=Decimal("100"), machine=machine
    )
    # Au moins 1 candidat avec nb_etiq adapté
    assert len(candidats) >= 1
    for c in candidats:
        assert INTERVALLE_MIN <= c.intervalle_mm <= INTERVALLE_MAX
