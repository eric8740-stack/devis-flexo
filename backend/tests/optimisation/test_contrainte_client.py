"""Tests règle contrainte client Sprint 13 S13.D.6.

CdC § 786-841 : le client final qui pose les étiquettes a sa propre
contrainte. Sa machine d'étiquetage utilise une cellule photoélectrique
qui doit détecter chaque étiquette individuellement. Si l'écart est
trop faible, la cellule confond deux étiquettes → pose ratée chez le client.

L'intervalle dev réel appliqué = MAX(min imprimeur, min client).
Si imposé par le client, on affiche un message pédagogique au commercial.
"""
from app.services.optimisation.regles.contrainte_client import (
    intervalle_dev_min_effectif,
)


def test_pas_de_contrainte_client_prend_min_imprimeur():
    res = intervalle_dev_min_effectif(
        intervalle_min_imprimeur=2.0, intervalle_min_client=0.0
    )
    assert res["intervalle_dev_min_applique_mm"] == 2.0
    assert res["est_contrainte_par_client"] is False
    assert res["message"] is None


def test_contrainte_client_inferieure_prend_min_imprimeur():
    """Client tolère 1 mm (cellule HD) mais imprimeur a 2 mm minimum
    technique → on garde 2 mm."""
    res = intervalle_dev_min_effectif(
        intervalle_min_imprimeur=2.0, intervalle_min_client=1.0
    )
    assert res["intervalle_dev_min_applique_mm"] == 2.0
    assert res["est_contrainte_par_client"] is False
    assert res["message"] is None


def test_contrainte_client_egale_pas_de_message():
    """Client = imprimeur : on applique, pas besoin de message spécifique."""
    res = intervalle_dev_min_effectif(
        intervalle_min_imprimeur=2.0, intervalle_min_client=2.0
    )
    assert res["intervalle_dev_min_applique_mm"] == 2.0
    assert res["est_contrainte_par_client"] is False
    assert res["message"] is None


def test_contrainte_client_superieure_force_intervalle():
    """Client a une machine ancienne (4 mm requis) → on impose 4 mm
    même si l'imprimeur pourrait faire 2 mm. Message pédagogique."""
    res = intervalle_dev_min_effectif(
        intervalle_min_imprimeur=2.0, intervalle_min_client=4.0
    )
    assert res["intervalle_dev_min_applique_mm"] == 4.0
    assert res["est_contrainte_par_client"] is True
    assert res["message"] is not None
    assert "4" in res["message"]
    assert "machine de pose" in res["message"].lower()
