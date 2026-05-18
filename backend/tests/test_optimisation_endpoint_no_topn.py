"""Tests endpoint /api/optimisation/calculer sans top_n (Sprint 13 avenant PR B).

Couvre :
  - L'endpoint renvoie TOUS les candidats viables (pas de cap à 3).
  - Le tri par score DESC est préservé.

Pour générer beaucoup de candidats, on onboarde un tenant avec un large
parc de cylindres et 2 machines (déjà fait dans test_optimisation_router).
"""
from fastapi.testclient import TestClient

from app.main import app
from tests.test_optimisation_router import (
    _onboard_tenant_minimal,
    cleanup_and_onboard,  # noqa: F401  (fixture exportée)
)

client = TestClient(app)


def test_endpoint_renvoie_tous_candidats_viables(cleanup_and_onboard):  # noqa: ARG001
    """Avec 6 cyl + 2 machines + format petit, on attend plus de 3 candidats
    viables. Le moteur retourne tout (plus de cap top_n)."""
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {
                "hauteur_mm": 30,
                "largeur_mm": 30,
                "rayon_angles_mm": 2.0,
                "forme_courbe": False,
            },
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Sprint 13 avenant : plus de cap à 3 — beaucoup de candidats possibles.
    assert body["nb_candidats"] > 3
    assert len(body["configurations"]) == body["nb_candidats"]


def test_endpoint_tri_par_score_desc(cleanup_and_onboard):  # noqa: ARG001
    """Le tri par score DESC est invariant — vérifié sur les nb_candidats configs."""
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {
                "hauteur_mm": 30,
                "largeur_mm": 30,
                "rayon_angles_mm": 2.0,
                "forme_courbe": False,
            },
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    scores = [c["score"] for c in body["configurations"]]
    assert scores == sorted(scores, reverse=True)
