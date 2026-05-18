"""Tests forçage nb_poses_laize (Sprint 13 avenant PR A commit 1).

Couvre :
  - Si N compatible avec laize_utile, le moteur produit une config qui
    bloque sur nb_poses_laize=N.
  - Si N > nb_poses_laize_max (incompatible), le candidat est skippé.

Note : le test du blocage utilise un format où plusieurs N sont possibles
en mode Auto ; on vérifie que le mode Forcer impose strictement le N
demandé.
"""
from fastapi.testclient import TestClient

from app.main import app
from tests.test_optimisation_router import (
    _onboard_tenant_minimal,
    cleanup_and_onboard,  # noqa: F401
)

client = TestClient(app)


def _post_optim(nb_poses_force: int | None) -> dict:
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
            **({"nb_poses_laize_force": nb_poses_force} if nb_poses_force is not None else {}),
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_force_compatible_calcule_intervalle_laize(cleanup_and_onboard):  # noqa: ARG001
    """Forcer nb_poses_laize=3 → toutes les configs ont exactement nb_poses_laize=3."""
    _onboard_tenant_minimal()
    body = _post_optim(nb_poses_force=3)
    assert body["nb_candidats"] >= 1
    for c in body["configurations"]:
        assert c["nb_poses_laize"] == 3


def test_force_incompatible_skip_candidat(cleanup_and_onboard):  # noqa: ARG001
    """Forcer un N énorme (50 poses) → 0 candidat viable car
    50 * largeur > laize_utile de toutes les machines."""
    _onboard_tenant_minimal()
    body = _post_optim(nb_poses_force=20)
    assert body["nb_candidats"] == 0
