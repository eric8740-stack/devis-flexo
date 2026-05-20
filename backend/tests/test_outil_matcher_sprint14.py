"""Tests Sprint 14 Lot 2 — service outil_matcher (TDD).

Couvre les 5 cas obligatoires du brief §3 Lot 2 :
1. Cas trivial : 1 cylindre 96 dents, étiquette 100×80 → 1 match correct
2. Cas multi-cylindre : 5 cylindres → liste triée par score décroissant
3. Cas aucun match : étiquette trop grande → [MatchOutil(cylindre_id=None, ...)]
4. Cas limite : étiquette pile à la limite du développé → match retenu
5. Cohérence V1a : paramètres cas test médian → un match valide retourné
   (n'invoque PAS le cost_engine, vérifie juste la cohérence du contrat)

Le service est PUR (pas de session DB) : il prend des CylindreMagnetique
détachés en argument. Le router scopera tenant et alimentera la liste
depuis la BDD.

Constantes métier partagées avec cylindre_matcher.py (sacred) — DUPLIQUÉES
volontairement pour éviter une dépendance d'outil_matcher.py vers le
package cost_engine intouchable.
"""
from decimal import Decimal

import pytest

from app.models import CylindreMagnetique
from app.services.outil_matcher import (
    COUT_NOUVEL_OUTIL_EUR_DEFAUT,
    PAS_CHENILLE_MM_DEFAULT,
    ContrainteOutil,
    MatchOutil,
    matcher_outils,
)


# ---------------------------------------------------------------------------
# Helpers : construire un CylindreMagnetique détaché (pas en BDD)
# ---------------------------------------------------------------------------


def _cyl(developpe_mm: Decimal, id_: int = 1) -> CylindreMagnetique:
    """Construit un CylindreMagnetique détaché pour les tests service pur."""
    c = CylindreMagnetique(
        entreprise_id=1,
        developpe_mm=developpe_mm,
        actif=True,
    )
    c.id = id_
    return c


def _contrainte(
    laize_etiq: Decimal = Decimal("80"),
    dev_etiq: Decimal = Decimal("100"),
    intervalle_dev: Decimal = Decimal("3"),
    intervalle_laize: Decimal = Decimal("3"),
    laize_machine: Decimal = Decimal("330"),
    nb_fronts_min: int = 1,
    nb_fronts_max: int = 10,
) -> ContrainteOutil:
    return ContrainteOutil(
        laize_etiquette_mm=laize_etiq,
        dev_etiquette_mm=dev_etiq,
        intervalle_dev_mm=intervalle_dev,
        intervalle_laize_mm=intervalle_laize,
        laize_machine_mm=laize_machine,
        nb_fronts_min=nb_fronts_min,
        nb_fronts_max=nb_fronts_max,
    )


# ---------------------------------------------------------------------------
# Cas 1 — trivial : 1 cylindre 96 dents, étiquette 100×80
# ---------------------------------------------------------------------------


def test_cas_trivial_1_cylindre_96_dents_etiquette_100x80():
    """1 cylindre Z=96 (développé 304.80 mm), étiquette 100×80, laize 330 mm.

    Calcul attendu :
        nb_dents = 96
        developpe_mm = 96 × 3.175 = 304.80
        pas_dev = dev_etiq + intervalle_dev = 100 + 3 = 103
        nb_poses_dev = floor(304.80 / 103) = 2
        pas_laize = laize_etiq + intervalle_laize = 80 + 3 = 83
        nb_poses_laize_max = floor(330 / 83) = 3  (mais on prend nb_fronts_max=10 plafond)
        → nb_poses_laize = 3 (max possible)
        nb_poses_total = 2 × 3 = 6
        surface utile = 6 × 100 × 80 = 48 000 mm²
        surface developpée = 304.80 × 330 = 100 584 mm²
        score = 48 000 / 100 584 ≈ 0.477
    """
    developpe = PAS_CHENILLE_MM_DEFAULT * Decimal(96)  # 304.80
    cylindres = [_cyl(developpe, id_=42)]
    contrainte = _contrainte()

    matches = matcher_outils(contrainte, cylindres)

    assert len(matches) == 1
    m = matches[0]
    assert m.cylindre_id == 42
    assert m.nb_dents == 96
    assert m.developpe_mm == developpe
    assert m.nb_poses_dev == 2
    assert m.nb_poses_laize == 3
    assert m.nb_poses_total == 6
    assert m.cout_outil_eur == Decimal(0)
    assert 0.0 < m.score_efficacite < 1.0
    # Cohérence du calcul score (tolérance large car formule à valider)
    surface_utile = 6 * 100 * 80
    surface_devel = float(developpe) * 330
    assert m.score_efficacite == pytest.approx(surface_utile / surface_devel, rel=1e-3)


# ---------------------------------------------------------------------------
# Cas 2 — multi-cylindre : 5 cylindres → triés par score décroissant
# ---------------------------------------------------------------------------


def test_cas_multi_cylindre_5_options_triees_par_score():
    """5 cylindres, certains plus efficaces que d'autres → tri DESC."""
    cylindres = [
        _cyl(PAS_CHENILLE_MM_DEFAULT * Decimal(z), id_=z)
        for z in (72, 80, 96, 104, 144)
    ]
    contrainte = _contrainte()

    matches = matcher_outils(contrainte, cylindres)

    # Au moins 2 cylindres compatibles (Z=72 trop petit pour pas 103 → skip
    # car nb_poses_dev=2 seulement si dev≥206 → Z=65 mini ; Z=72 donne dev
    # 228.6 → nb_poses_dev=2, score plus faible que Z=96 ; etc.)
    assert len(matches) >= 2, f"attendu ≥ 2 matches, got {len(matches)}"

    # Tri strict décroissant par score
    scores = [m.score_efficacite for m in matches]
    assert scores == sorted(scores, reverse=True), (
        f"matches non triés par score décroissant : {scores}"
    )

    # Tous les cylindre_id retournés sont issus de la liste fournie
    ids_attendus = {72, 80, 96, 104, 144}
    for m in matches:
        assert m.cylindre_id in ids_attendus
        assert m.cylindre_id is not None  # cas 2 : tous existants


# ---------------------------------------------------------------------------
# Cas 3 — aucun match : étiquette trop grande → option "nouvel outil"
# ---------------------------------------------------------------------------


def test_cas_aucun_match_etiquette_trop_grande_propose_nouvel_outil():
    """Étiquette 500 mm de dev > tous les développés 96-144 dents → vide.

    Le service doit retourner exactement 1 MatchOutil avec cylindre_id=None
    (option fabriquer un nouvel outil sur mesure).
    """
    cylindres = [
        _cyl(PAS_CHENILLE_MM_DEFAULT * Decimal(z), id_=z)
        for z in (96, 104, 120, 144)
    ]
    contrainte = _contrainte(
        dev_etiq=Decimal("500"),  # trop grand pour le parc
        laize_etiq=Decimal("80"),
    )

    matches = matcher_outils(contrainte, cylindres)

    assert len(matches) == 1, (
        f"cas 3 : exactement 1 option 'nouvel outil', got {len(matches)}"
    )
    m = matches[0]
    assert m.cylindre_id is None, "cas 3 : cylindre_id doit être None (nouvel outil)"
    assert m.nb_dents >= 1
    assert m.developpe_mm > Decimal("500")  # cylindre dimensionné pour l'étiquette
    assert m.nb_poses_dev >= 1
    assert m.cout_outil_eur == COUT_NOUVEL_OUTIL_EUR_DEFAUT
    assert 0.0 < m.score_efficacite <= 1.0


# ---------------------------------------------------------------------------
# Cas 4 — limite : étiquette pile à la limite du développé
# ---------------------------------------------------------------------------


def test_cas_limite_etiquette_pile_a_la_limite_du_developpe():
    """Cylindre Z=96 (dev 304.80 mm), étiquette dev 300 + intervalle 3 → pas 303
    → nb_poses_dev = floor(304.80 / 303) = 1. C'est juste-juste, mais valide.
    """
    developpe = PAS_CHENILLE_MM_DEFAULT * Decimal(96)
    cylindres = [_cyl(developpe, id_=99)]
    contrainte = _contrainte(
        dev_etiq=Decimal("300"),
        intervalle_dev=Decimal("3"),
        laize_etiq=Decimal("80"),
    )

    matches = matcher_outils(contrainte, cylindres)

    # Un cylindre compatible (pile à la limite) doit ressortir, pas
    # l'option "nouvel outil".
    assert len(matches) == 1
    m = matches[0]
    assert m.cylindre_id == 99
    assert m.nb_poses_dev == 1, "limite : 1 pose dev attendue"


def test_cas_limite_inferieure_etiquette_juste_trop_grande():
    """Cylindre Z=96 (dev 304.80 mm), étiquette dev 305 → pas > developpe →
    aucun match existant → option 'nouvel outil'.
    """
    developpe = PAS_CHENILLE_MM_DEFAULT * Decimal(96)
    cylindres = [_cyl(developpe, id_=99)]
    contrainte = _contrainte(
        dev_etiq=Decimal("305"),
        intervalle_dev=Decimal("3"),
    )

    matches = matcher_outils(contrainte, cylindres)

    assert len(matches) == 1
    assert matches[0].cylindre_id is None, (
        "dev 305+3=308 > 304.80 → cylindre Z=96 incompatible → nouvel outil"
    )


# ---------------------------------------------------------------------------
# Cas 5 — cohérence avec cas test médian V1a (1449,09 € sacred)
# ---------------------------------------------------------------------------


def test_cas_coherence_v1a_parametres_retournent_un_match_valide():
    """Cas test médian V1a (sacred 1449,09 €) :
        format 60×40 mm (laize × dev)
        machine Mark Andy P5 laize_max=330 mm
        intervalles défaut 3 mm
        nb_poses_largeur=3 (= nb_fronts attendu)

    Le matcher Sprint 14 NE recalcule PAS le cost_engine — il propose des
    options outil compatibles. On vérifie ici qu'au moins un match valide
    avec nb_poses_laize=3 est proposé sur un parc cohérent, prouvant que
    le contrat ne casse pas le scénario V1a.

    Catalogue cylindres ICE standard (cf. cylindre_magnetique.py docstring) :
    72, 80, 82, 84, 86, 88, 90, 92, 96, 98, 103, 104, 112, 116, 128, 132,
    134, 136, 144.
    """
    cylindres = [
        _cyl(PAS_CHENILLE_MM_DEFAULT * Decimal(z), id_=z)
        for z in (72, 80, 84, 88, 96, 104, 112, 128, 134, 144)
    ]
    # nb_fronts_max=3 force le matcher à respecter le V1a nb_poses_largeur=3
    # (la machine en supporterait plus, mais V1a est figée à 3 fronts).
    contrainte = _contrainte(
        laize_etiq=Decimal("60"),    # V1a : largeur étiquette
        dev_etiq=Decimal("40"),      # V1a : hauteur étiquette
        intervalle_dev=Decimal("3"),
        intervalle_laize=Decimal("3"),
        laize_machine=Decimal("330"),
        nb_fronts_max=3,
    )

    matches = matcher_outils(contrainte, cylindres)

    assert len(matches) >= 1, "V1a doit produire au moins 1 match existant"
    # Tous les matches doivent respecter le plafond nb_fronts_max=3
    for m in matches:
        assert m.nb_poses_laize <= 3, (
            f"V1a nb_fronts_max=3 violé : nb_poses_laize={m.nb_poses_laize}"
        )
    # Au moins un match doit utiliser pleinement les 3 fronts (le pattern V1a)
    matches_3_fronts = [m for m in matches if m.nb_poses_laize == 3]
    assert matches_3_fronts, (
        "V1a : au moins un match doit utiliser nb_poses_laize=3 (V1a sacred pattern)"
    )
    # Et aucune erreur ne doit faire chuter le matcher (cohérence contrat)
    for m in matches:
        assert m.cylindre_id in (None, *(c.id for c in cylindres))
        assert m.nb_poses_dev >= 1
        assert m.nb_poses_laize >= 1
        assert m.nb_poses_total == m.nb_poses_dev * m.nb_poses_laize
        assert 0.0 < m.score_efficacite <= 1.0
