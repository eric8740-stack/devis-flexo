"""Tests d'intégration de l'orchestrateur Sprint 13 S13.D.7a.

Vérifie que les 6 règles métier (D.1-D.6) coopèrent correctement dans
le flux principal `optimiser_pose()`. Ce sont des tests E2E sur le
service pur (pas de DB ni FastAPI ici).
"""
import math

import pytest

from app.data.catalogue_defaults import get_bareme_by_code
from app.services.optimisation.moteur import optimiser_pose
from app.services.optimisation.types import (
    ContrainteClient,
    Cylindre,
    Format,
    Machine,
    OptimisationInput,
    OptionFabrication,
)


BAREME_ECHEN = get_bareme_by_code("echenillage_ice")["bareme_data"]
BAREME_BANANE = get_bareme_by_code("effet_banane_ice")["bareme_data"]
BAREME_COMP = get_bareme_by_code("compensation_laize_dev_ice")["bareme_data"]
BAREME_CONFORT = get_bareme_by_code("confort_roulage_ice")["bareme_data"]


def _input_base(
    cylindres: list[Cylindre],
    machines: list[Machine],
    format: Format,
    nb_couleurs: int = 4,
    options: list[OptionFabrication] | None = None,
    intervalle_min_imp: float = 2.0,
    intervalle_min_client: float = 0.0,
) -> OptimisationInput:
    return OptimisationInput(
        format=format,
        intervalle_dev_min_mm=intervalle_min_imp,
        nb_couleurs_impression=nb_couleurs,
        quantite=10_000,
        options=options or [],
        cylindres=cylindres,
        machines=machines,
        bareme_echenillage=BAREME_ECHEN,
        bareme_effet_banane=BAREME_BANANE,
        bareme_compensation=BAREME_COMP,
        bareme_confort_roulage=BAREME_CONFORT,
        contrainte_client=ContrainteClient(
            intervalle_dev_min_mm=intervalle_min_client
        ),
    )


def _machine_2200() -> Machine:
    return Machine(
        id=1,
        nom="Mark Andy 2200",
        laize_utile_mm=320,
        nb_groupes_couleurs=8,
        nb_postes_decoupe=1,
        vitesse_pratique_m_min=70,
        cout_horaire_eur=70.0,
        options=["UV"],
    )


def _machine_xflex() -> Machine:
    return Machine(
        id=2,
        nom="OMET XFlex 330",
        laize_utile_mm=330,
        nb_groupes_couleurs=10,
        nb_postes_decoupe=2,
        vitesse_pratique_m_min=80,
        cout_horaire_eur=95.0,
        options=["UV", "hot_stamping", "retournement_laize"],
    )


# ---------------------------------------------------------------------------
# Cas simples
# ---------------------------------------------------------------------------


def test_cas_simple_un_cylindre_une_machine_donne_au_moins_une_config():
    """Cyl 304.8 mm (96 dents) + Mark Andy 2200 (laize 320) + format 70×50 CMJN
    → au moins 1 config viable."""
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=304.8)],
        machines=[_machine_2200()],
        format=Format(hauteur_mm=70, largeur_mm=50),
    )
    out = optimiser_pose(inp)
    assert out.nb_candidats >= 1
    # Sprint 13 avenant : plus de cap top_n côté backend.
    # Sanity : config cohérente
    c = out.configurations[0]
    assert c.cylindre_id == 1
    assert c.machine_id == 1
    assert c.nb_poses_dev >= 1
    assert c.nb_poses_laize >= 1
    assert c.nb_poses_total == c.nb_poses_dev * c.nb_poses_laize


def test_intervalle_dev_reel_coherent_avec_format():
    """Cyl 254 mm (80 dents), format hauteur 40 mm, intervalle min 2 :
    nb_poses_dev = floor(254 / 42) = 6, intervalle_réel = 254/6 − 40 ≈ 2.33 mm
    → palier 'parfait' du barème échenillage ICE (≤ 3 mm)."""
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=254.0)],
        machines=[_machine_2200()],
        format=Format(hauteur_mm=40, largeur_mm=30),
    )
    out = optimiser_pose(inp)
    c = out.configurations[0]
    assert c.nb_poses_dev == 6
    assert c.intervalle_dev_reel_mm == pytest.approx(2.33, abs=0.01)
    assert c.qualite_echenillage == "parfait"


def test_tous_candidats_viables_retournes_tries_par_score_desc():
    """Sprint 13 avenant : le moteur retourne TOUS les candidats viables
    (pas de top_n côté backend). Le filtrage par score est UI only.

    6 cylindres × 1 machine × multi-variantes laize peut générer beaucoup
    de candidats. Cyls en mm réels (dents × 3.175) :
    [228.6, 254.0, 279.4, 304.8, 330.2, 355.6]. On vérifie que le moteur
    renvoie au moins 3 candidats (donc plus de cap à 3) ET que le tri
    score DESC est préservé.
    """
    cyls = [
        Cylindre(id=i, developpe_mm=dev)
        for i, dev in enumerate(
            [228.6, 254.0, 279.4, 304.8, 330.2, 355.6], start=1
        )
    ]
    inp = _input_base(
        cylindres=cyls,
        machines=[_machine_2200()],
        format=Format(hauteur_mm=30, largeur_mm=30),
    )
    out = optimiser_pose(inp)
    # Sprint 13 avenant : pas de top_n cap. Avec 6 cyl + 3 variantes
    # potentielles chacun, on a beaucoup plus que 3 candidats viables.
    assert out.nb_candidats > 3
    # Tri par score DESC (invariant inchangé)
    scores = [c.score for c in out.configurations]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Filtres durs
# ---------------------------------------------------------------------------


def test_effet_banane_exclut_cyl_trop_petit():
    """Cyl 228.6 mm (72 dents) + format laize 200 → effet banane exclut.
    Avec largeur 200 et laize_utile 330, variante max = 1 ; plaque = 200 mm
    → Z mini ICE = 304.8 mm. Cyl 228.6 < 304.8 → exclu."""
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=228.6)],
        machines=[_machine_xflex()],  # laize 330
        format=Format(hauteur_mm=50, largeur_mm=200),
    )
    out = optimiser_pose(inp)
    # 0 configs viables — l'unique variante laize impose un Z mini > 228.6.
    assert out.nb_candidats == 0
    assert out.message_filtrage is not None
    assert "éliminé" in out.message_filtrage


def test_capacite_couleurs_filtre_machine():
    """10 couleurs CMJN+spot demandées, machine 8 groupes → exclue.
    Machine xflex (10 groupes) → OK."""
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=304.8)],  # 96 dents
        machines=[_machine_2200(), _machine_xflex()],
        format=Format(hauteur_mm=70, largeur_mm=50),
        nb_couleurs=10,
    )
    out = optimiser_pose(inp)
    # Seules les configs sur xflex (machine_id=2) survivent
    assert out.nb_candidats >= 1
    for c in out.configurations:
        assert c.machine_id == 2


def test_module_manquant_exclut_machine_pour_option():
    """Option dorure_chaud (requiert hot_stamping). Mark Andy 2200 n'a
    pas hot_stamping → exclue. Xflex OK."""
    dorure = OptionFabrication(
        code="dorure_chaud",
        libelle="Dorure à chaud",
        coef_vitesse_impact=0.75,
        coef_gache_impact=1.15,
        modules_speciaux_requis=["hot_stamping"],
    )
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=304.8)],  # 96 dents
        machines=[_machine_2200(), _machine_xflex()],
        format=Format(hauteur_mm=70, largeur_mm=50),
        options=[dorure],
    )
    out = optimiser_pose(inp)
    assert out.nb_candidats >= 1
    for c in out.configurations:
        assert c.machine_id == 2  # uniquement xflex


# ---------------------------------------------------------------------------
# Contrainte client
# ---------------------------------------------------------------------------


def test_contrainte_client_force_intervalle_dev_min():
    """Client impose 4 mm. Cyl 304.8 (96 dents), format 30×30.
    nb_poses_dev = floor(304.8 / 34) = 8. intervalle réel = 304.8/8 − 30 = 8.1 mm."""
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=304.8)],
        machines=[_machine_2200()],
        format=Format(hauteur_mm=30, largeur_mm=30),
        intervalle_min_imp=2.0,
        intervalle_min_client=4.0,
    )
    out = optimiser_pose(inp)
    assert out.intervalle_dev_min_applique_mm == 4.0
    assert out.message_contrainte_client is not None
    c = out.configurations[0]
    assert c.nb_poses_dev == 8
    assert c.intervalle_dev_reel_mm == pytest.approx(8.1, abs=0.01)


# ---------------------------------------------------------------------------
# Coefficients cumulatifs (options + règles)
# ---------------------------------------------------------------------------


def test_options_cumulent_coefs_multiplicativement():
    """Vernis sélectif (0.95) × Numérotation (0.90) = 0.855 sur coef_vitesse."""
    vernis = OptionFabrication(
        code="vernis_selectif",
        libelle="Vernis sélectif",
        coef_vitesse_impact=0.95,
        coef_gache_impact=1.03,
        groupes_couleurs_requis=1,
    )
    num = OptionFabrication(
        code="numerotation",
        libelle="Numérotation",
        coef_vitesse_impact=0.90,
        coef_gache_impact=1.05,
    )
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=304.8)],  # 96 dents
        machines=[_machine_2200()],
        format=Format(hauteur_mm=30, largeur_mm=30),
        options=[vernis, num],
    )
    out = optimiser_pose(inp)
    c = out.configurations[0]
    assert math.isclose(c.coef_vitesse_options, 0.855, abs_tol=1e-4)
    assert math.isclose(c.coef_gache_options, 1.0815, abs_tol=1e-4)


def test_format_rayon_5mm_donne_coef_confort_108():
    """Format avec rayon 5 mm → coef confort_rayon = 1.08 (barème ICE)."""
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=304.8)],  # 96 dents
        machines=[_machine_2200()],
        format=Format(hauteur_mm=30, largeur_mm=30, rayon_angles_mm=5.0),
    )
    out = optimiser_pose(inp)
    c = out.configurations[0]
    assert c.coef_confort_rayon == 1.08


def test_forme_courbe_donne_coef_115():
    inp = _input_base(
        cylindres=[Cylindre(id=1, developpe_mm=304.8)],  # 96 dents
        machines=[_machine_2200()],
        format=Format(
            hauteur_mm=30, largeur_mm=30, rayon_angles_mm=0.0, forme_courbe=True
        ),
    )
    out = optimiser_pose(inp)
    c = out.configurations[0]
    assert c.coef_confort_rayon == 1.15
