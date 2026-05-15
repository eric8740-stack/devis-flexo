"""Tests règle capacité couleurs Sprint 13 S13.D.5 (filtre dur).

CdC § 1283-1324 : à la saisie d'un devis, la machine doit avoir assez
de groupes couleurs (stations flexo standard) pour gérer les couleurs
d'impression + les options qui consomment des stations. Et elle doit
avoir les modules spéciaux requis par chaque option (hot_stamping,
retournement_laize, etc.).

Filtre dur : si la machine n'a pas la capacité ou un module manquant,
elle est éliminée pour ce devis.
"""
from app.services.optimisation.regles.capacite_couleurs import (
    verifier_capacite,
)
from app.services.optimisation.types import Machine, OptionFabrication


def _machine_2200_8_groupes() -> Machine:
    return Machine(
        id=1,
        nom="Mark Andy 2200",
        laize_utile_mm=320,
        nb_groupes_couleurs=8,
        nb_postes_decoupe=1,
        options=["UV"],
    )


def _machine_xflex_10_groupes() -> Machine:
    return Machine(
        id=2,
        nom="OMET XFlex 330",
        laize_utile_mm=330,
        nb_groupes_couleurs=10,
        nb_postes_decoupe=2,
        options=["UV", "hot_stamping", "retournement_laize", "cold_foil"],
    )


def test_machine_assez_capacite_simple_4_couleurs():
    """Mark Andy 2200 (8 groupes) + 4 couleurs CMJN + 0 option → OK."""
    res = verifier_capacite(
        machine=_machine_2200_8_groupes(),
        nb_couleurs=4,
        options_selectionnees=[],
    )
    assert res.ok is True


def test_machine_capacite_insuffisante_couleurs_seules():
    """Mark Andy 2200 (8 groupes) + 10 couleurs → KO, 2 en trop."""
    res = verifier_capacite(
        machine=_machine_2200_8_groupes(),
        nb_couleurs=10,
        options_selectionnees=[],
    )
    assert res.ok is False
    assert res.raison == "capacite_insuffisante"
    assert "2" in res.message  # 2 stations en trop


def test_machine_capacite_juste_atteinte():
    """8 couleurs sur 8 groupes : utilise tout, mais OK (pas négatif)."""
    res = verifier_capacite(
        machine=_machine_2200_8_groupes(),
        nb_couleurs=8,
        options_selectionnees=[],
    )
    assert res.ok is True


def test_option_consomme_groupes_couleurs():
    """4 CMJN + vernis sélectif (1 groupe) + back_print (1 groupe) = 6 sur 8."""
    vernis = OptionFabrication(
        code="vernis_selectif",
        libelle="Vernis sélectif",
        groupes_couleurs_requis=1,
    )
    back_print = OptionFabrication(
        code="back_print",
        libelle="Back print",
        groupes_couleurs_requis=1,
    )
    res = verifier_capacite(
        machine=_machine_2200_8_groupes(),
        nb_couleurs=4,
        options_selectionnees=[vernis, back_print],
    )
    assert res.ok is True


def test_option_excede_capacite():
    """6 couleurs + livret (2 groupes) sur 8 → KO (8 utilisés mais le
    test critique c'est si on dépasse)."""
    livret = OptionFabrication(
        code="livret",
        libelle="Étiquettes livret",
        groupes_couleurs_requis=2,
        modules_speciaux_requis=["retournement_laize"],
    )
    res = verifier_capacite(
        machine=_machine_xflex_10_groupes(),
        nb_couleurs=10,
        options_selectionnees=[livret],
    )
    assert res.ok is False
    assert res.raison == "capacite_insuffisante"


def test_module_manquant_dorure_chaud_sur_machine_sans_hot_stamping():
    """Mark Andy 2200 n'a PAS hot_stamping → dorure_chaud exige ce
    module → machine éliminée."""
    dorure = OptionFabrication(
        code="dorure_chaud",
        libelle="Dorure à chaud",
        modules_speciaux_requis=["hot_stamping"],
    )
    res = verifier_capacite(
        machine=_machine_2200_8_groupes(),
        nb_couleurs=4,
        options_selectionnees=[dorure],
    )
    assert res.ok is False
    assert res.raison == "module_manquant"
    assert "hot_stamping" in res.message
    assert "Dorure" in res.message or "dorure" in res.message


def test_module_present_dorure_chaud_passe_sur_xflex():
    """OMET XFlex 330 a hot_stamping → dorure_chaud OK."""
    dorure = OptionFabrication(
        code="dorure_chaud",
        libelle="Dorure à chaud",
        modules_speciaux_requis=["hot_stamping"],
    )
    res = verifier_capacite(
        machine=_machine_xflex_10_groupes(),
        nb_couleurs=4,
        options_selectionnees=[dorure],
    )
    assert res.ok is True


def test_option_avec_plusieurs_modules_un_manquant():
    """Si AU MOINS UN module manque, on rejette (pas de demi-mesure)."""
    livret = OptionFabrication(
        code="livret",
        libelle="Étiquettes livret",
        groupes_couleurs_requis=2,
        # retournement_laize : OK sur XFlex
        # vernis_liberateur : ABSENT sur XFlex
        modules_speciaux_requis=["retournement_laize", "vernis_liberateur"],
    )
    res = verifier_capacite(
        machine=_machine_xflex_10_groupes(),
        nb_couleurs=4,
        options_selectionnees=[livret],
    )
    assert res.ok is False
    assert res.raison == "module_manquant"
    assert "vernis_liberateur" in res.message
