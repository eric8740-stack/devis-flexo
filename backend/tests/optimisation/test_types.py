"""Tests des types/dataclasses du moteur d'optimisation Sprint 13 S13.D.0.

Vérifie :
  - Construction par défaut des dataclasses (champs optionnels avec
    `field(default_factory=...)` ne plantent pas).
  - Le coef_vitesse_final cumule bien les 5 sous-coefficients (CdC § 758)
    en produit multiplicatif.
  - Le coef_gache_final cumule échenillage × options (CdC § 1138).
"""
import math

from app.services.optimisation.types import (
    ConfigurationPose,
    ContrainteClient,
    Cylindre,
    Format,
    Machine,
    OptimisationInput,
    OptionFabrication,
)


def test_format_default_radius_is_standard_2mm():
    f = Format(hauteur_mm=70, largeur_mm=50)
    assert f.rayon_angles_mm == 2.0
    assert f.forme_courbe is False


def test_optimisation_input_construit_avec_defauts():
    inp = OptimisationInput(
        format=Format(hauteur_mm=100, largeur_mm=80),
        intervalle_dev_min_mm=2.0,
        nb_couleurs_impression=4,
        quantite=10_000,
    )
    assert inp.cylindres == []
    assert inp.machines == []
    assert inp.matiere_est_transparente is False
    assert inp.contrainte_client.intervalle_dev_min_mm == 0.0


def test_machine_options_default_empty_list():
    m = Machine(
        id=1,
        nom="Test 2200",
        laize_utile_mm=320,
        nb_groupes_couleurs=8,
    )
    assert m.options == []
    assert m.nb_postes_decoupe == 1


def test_coef_vitesse_final_cumule_5_sources():
    """coef_vitesse_final = echenillage × consolidation × confort_rayon
    × quinconce × options (CdC § 758)."""
    config = ConfigurationPose(
        cylindre_id=1,
        machine_id=1,
        nb_poses_dev=4,
        nb_poses_laize=3,
        nb_poses_total=12,
        intervalle_dev_reel_mm=3.0,
        intervalle_laize_reel_mm=2.0,
        largeur_plaque_mm=160.0,
        z_mini_effet_banane=96.0,
        coef_vitesse_echenillage=1.00,
        coef_consolidation=1.00,
        coef_confort_rayon=1.08,
        coef_quinconce=1.10,
        coef_vitesse_options=0.95,
    )
    # 1.00 × 1.00 × 1.08 × 1.10 × 0.95 = 1.1286
    assert math.isclose(config.coef_vitesse_final, 1.1286, abs_tol=1e-4)


def test_coef_gache_final_cumule_echenillage_et_options():
    config = ConfigurationPose(
        cylindre_id=1,
        machine_id=1,
        nb_poses_dev=4,
        nb_poses_laize=3,
        nb_poses_total=12,
        intervalle_dev_reel_mm=5.0,
        intervalle_laize_reel_mm=2.0,
        largeur_plaque_mm=160.0,
        z_mini_effet_banane=96.0,
        coef_gache_echenillage=1.08,
        coef_gache_options=1.10,
    )
    assert math.isclose(config.coef_gache_final, 1.188, abs_tol=1e-4)


def test_contrainte_client_default_zero():
    """ContrainteClient par défaut → intervalle_dev_min_mm=0 (pas de
    contrainte client, on prend le minimum imprimeur)."""
    cc = ContrainteClient()
    assert cc.intervalle_dev_min_mm == 0.0


def test_option_fabrication_construit_simple():
    opt = OptionFabrication(
        code="dorure_chaud",
        libelle="Dorure à chaud",
        coef_vitesse_impact=0.75,
        coef_gache_impact=1.15,
        ajoute_temps_calage_min=25,
        modules_speciaux_requis=["hot_stamping"],
    )
    assert opt.modules_speciaux_requis == ["hot_stamping"]
    assert opt.groupes_couleurs_requis == 0  # default


def test_cylindre_immutable():
    """Les Cylindre/Format/Machine sont frozen → modification doit lever
    FrozenInstanceError (sanity check immutabilité)."""
    cyl = Cylindre(id=1, developpe_mm=96.0)
    import dataclasses
    try:
        cyl.developpe_mm = 104.0  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("Cylindre devrait être frozen")
