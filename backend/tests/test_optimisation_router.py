"""Tests du router /api/optimisation — Sprint 13 Lot S13.D.7b.

Couvre :
  - 409 si tenant pas onboardé (pas de cylindres/machines)
  - 200 happy path : top 3 viable après onboarding
  - 422 si option_code inconnu
  - 403 si user n'a pas le module flexocompare
  - Isolation tenant : user B ne voit pas les cylindres de A

NB : on s'appuie sur le service onboarding (S13.C.2) pour materialiser
le catalogue minimal pour chaque tenant avant le test, plutot que de
poser des rows a la main — c'est plus realiste et reutilise le code
deja teste.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import (
    Bareme,
    CylindreMagnetique,
    MachineImprimerie,
    Matiere,
    OptionFabrication,
)

client = TestClient(app)


@pytest.fixture
def cleanup_and_onboard():
    """Purge les rows S13.B des tenants test + (en option) appelle
    l'onboarding via API pour le tenant 1 (admin demo).
    """
    db: Session = SessionLocal()
    try:
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
        yield
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
    finally:
        db.close()


def _onboard_tenant_minimal():
    """Onboarde via l'API : 6 cylindres représentatifs + 2 machines +
    options minimales + barèmes (toujours 4)."""
    payload = {
        "cylindres_developpes_mm": [72, 96, 104, 112, 128, 144],
        "machines_codes": ["mark_andy_2200", "omet_xflex_330"],
        "matieres_codes": [],
        "options_codes": ["vernis_selectif", "dorure_chaud"],
    }
    r = client.post("/api/onboarding/initialiser-catalogues", json=payload)
    assert r.status_code == 201, r.text


# ---------------------------------------------------------------------------
# Cas heureux
# ---------------------------------------------------------------------------


def test_post_calculer_happy_path(cleanup_and_onboard):
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
    assert body["nb_candidats"] >= 1
    assert body["nb_candidats"] <= 3
    assert body["intervalle_dev_min_applique_mm"] == 2.0
    # Au moins 1 config a score > 0
    assert any(c["score"] > 0 for c in body["configurations"])
    # Chaque config a tous les coefs cumulés
    for c in body["configurations"]:
        assert c["coef_vitesse_final"] > 0
        assert c["coef_gache_final"] > 0


def test_post_calculer_avec_options_applique_coefs(cleanup_and_onboard):
    """Avec vernis_selectif (coef_vitesse_impact=0.95, pas de module
    spécial requis), toutes les configs portent ce coef. On vérifie que
    le moteur applique bien les coefs des options."""
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": ["vernis_selectif"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nb_candidats"] >= 1
    for c in body["configurations"]:
        # Coef vitesse vernis_selectif = 0.95 (catalogue_defaults.py)
        assert c["coef_vitesse_options"] == 0.95


def test_post_calculer_contrainte_client_force_min(cleanup_and_onboard):
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
            "contrainte_client": {"intervalle_dev_min_mm": 4.0},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intervalle_dev_min_applique_mm"] == 4.0
    assert body["message_contrainte_client"] is not None


# ---------------------------------------------------------------------------
# Erreurs
# ---------------------------------------------------------------------------


def test_post_calculer_409_si_pas_onboarde(cleanup_and_onboard):
    """Sans onboarding, le tenant n'a aucun cylindre/machine → 409."""
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 409
    assert "onboarding" in r.json()["detail"].lower()


def test_post_calculer_422_si_option_code_inconnu(cleanup_and_onboard):
    _onboard_tenant_minimal()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": ["option_qui_nexiste_pas"],
        },
    )
    assert r.status_code == 422
    assert "option_qui_nexiste_pas" in r.json()["detail"]


def test_post_calculer_403_si_pas_module_flexocompare(
    cleanup_and_onboard, as_user_flexocheck_only
):
    """User check-only (sans flexocompare) → 403."""
    _onboard_tenant_minimal()  # onboard fait sur le tenant check-only
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 403
    assert "flexocompare" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Isolation tenant
# ---------------------------------------------------------------------------


def test_isolation_tenant_user_b_voit_pas_catalogue_de_a(
    cleanup_and_onboard, switch_to_user_b
):
    """User A s'onboarde. User B (autre tenant) → 409 car son propre
    catalogue est vide. Garantit qu'on ne fuit pas les cylindres entre
    tenants."""
    _onboard_tenant_minimal()  # User A (entreprise_id=1)
    switch_to_user_b()
    r = client.post(
        "/api/optimisation/calculer",
        json={
            "format": {"hauteur_mm": 30, "largeur_mm": 30},
            "intervalle_dev_min_mm": 2.0,
            "nb_couleurs_impression": 4,
            "quantite": 10_000,
            "options_codes": [],
        },
    )
    assert r.status_code == 409
