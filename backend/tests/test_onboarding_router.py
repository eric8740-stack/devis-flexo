"""Tests du router /api/onboarding — Sprint 13 Lot S13.C.2.

Couvre :
  - GET /catalogue-defaults : structure + comptages 19/3/30/20/4
  - GET /status : faux avant onboarding, vrai après
  - POST /initialiser-catalogues happy path (compteurs corrects)
  - POST refuse si déjà initialisé (409)
  - POST refuse code matière inconnu (422)
  - POST refuse cylindre développé absent du catalogue (422)
  - Isolation tenant : 2 entreprises peuvent s'onboarder indépendamment
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
def cleanup_tenant_rows():
    """Avant chaque test, on purge les rows S13.B associées aux entreprises
    de test (entreprise demo id=1, isolation B id=2). Les autouse seed
    reset les entreprises mais pas ces nouvelles tables.
    """
    db: Session = SessionLocal()
    try:
        for ent_id in (1, 2):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
        yield
        # Teardown idem pour ne pas polluer les tests suivants
        for ent_id in (1, 2):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /catalogue-defaults
# ---------------------------------------------------------------------------


def test_get_catalogue_defaults_renvoie_tous_les_catalogues():
    r = client.get("/api/onboarding/catalogue-defaults")
    assert r.status_code == 200
    body = r.json()
    assert len(body["cylindres_developpes_mm"]) == 21  # Brief #28 : parc 21 cyls
    assert len(body["machines"]) == 3
    assert len(body["matieres"]) == 30
    assert len(body["options"]) == 20
    assert len(body["baremes"]) == 4
    # Sanity : on retrouve bien Mark Andy
    codes_machines = [m["code"] for m in body["machines"]]
    assert "mark_andy_2200" in codes_machines


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


def test_status_false_avant_onboarding(cleanup_tenant_rows):
    r = client.get("/api/onboarding/status")
    assert r.status_code == 200
    assert r.json() == {"catalogue_initialise": False}


def test_status_true_apres_onboarding(cleanup_tenant_rows):
    # Onboarding minimal d'abord — 304.8 mm = 96 dents (cf. fix Cas B)
    r = client.post(
        "/api/onboarding/initialiser-catalogues",
        json={
            "cylindres_developpes_mm": [304.8],
            "machines_codes": ["mark_andy_2200"],
            "matieres_codes": [],
            "options_codes": [],
        },
    )
    assert r.status_code == 201
    # Maintenant status doit être à True
    r = client.get("/api/onboarding/status")
    assert r.json() == {"catalogue_initialise": True}


# ---------------------------------------------------------------------------
# POST /initialiser-catalogues — happy path
# ---------------------------------------------------------------------------


def test_post_initialiser_catalogues_happy_path(cleanup_tenant_rows):
    # Brief #28 : 72 retiré du parc compte demo (228.6 mm n'est plus valide).
    # On utilise 254.0 (80 dents) comme cyl bas de gamme pour exercer le cas
    # "petit cylindre". Autres valeurs mm = dents × 3.175 :
    # 80→254.0, 96→304.8, 104→330.2, 144→457.2.
    payload = {
        "cylindres_developpes_mm": [254.0, 304.8, 330.2, 457.2],
        "machines_codes": ["mark_andy_2200", "omet_xflex_330"],
        "matieres_codes": ["PAP_COUCHE_BRILL_80", "BOPP_TRANSP_50"],
        "options_codes": ["vernis_selectif", "dorure_chaud", "numerotation"],
    }
    r = client.post("/api/onboarding/initialiser-catalogues", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cylindres"] == 4
    assert body["machines"] == 2
    assert body["matieres"] == 2
    assert body["options"] == 3
    assert body["baremes"] == 4  # toujours chargés systématiquement
    assert body["total"] == 4 + 2 + 2 + 3 + 4

    # Vérif persistence (count via DB pour s'assurer du scope tenant)
    db: Session = SessionLocal()
    try:
        assert db.query(CylindreMagnetique).filter_by(entreprise_id=1).count() == 4
        assert db.query(MachineImprimerie).filter_by(entreprise_id=1).count() == 2
        assert db.query(Matiere).filter_by(entreprise_id=1).count() == 2
        assert db.query(OptionFabrication).filter_by(entreprise_id=1).count() == 3
        assert db.query(Bareme).filter_by(entreprise_id=1).count() == 4
        # Une matière transparente bien marquée
        bopp = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, code="BOPP_TRANSP_50")
            .first()
        )
        assert bopp is not None
        assert bopp.est_transparent is True
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST — refus si déjà initialisé
# ---------------------------------------------------------------------------


def test_post_refuse_si_deja_initialise(cleanup_tenant_rows):
    payload = {
        "cylindres_developpes_mm": [304.8],  # 96 dents × 3.175
        "machines_codes": ["mark_andy_2200"],
        "matieres_codes": [],
        "options_codes": [],
    }
    r1 = client.post("/api/onboarding/initialiser-catalogues", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/onboarding/initialiser-catalogues", json=payload)
    assert r2.status_code == 409
    assert "déjà initialisé" in r2.json()["detail"]


# ---------------------------------------------------------------------------
# POST — refus codes inconnus
# ---------------------------------------------------------------------------


def test_post_refuse_code_matiere_inconnu(cleanup_tenant_rows):
    r = client.post(
        "/api/onboarding/initialiser-catalogues",
        json={
            "cylindres_developpes_mm": [304.8],  # 96 dents
            "machines_codes": [],
            "matieres_codes": ["INEXISTANT_42"],
            "options_codes": [],
        },
    )
    assert r.status_code == 422
    assert "INEXISTANT_42" in r.json()["detail"]


def test_post_refuse_cylindre_hors_catalogue(cleanup_tenant_rows):
    # 314.2 mm n'est dérivé d'AUCUNE dent standard (98 dents = 311.15,
    # 103 dents = 327.025 — donc 314.2 tombe entre les deux).
    r = client.post(
        "/api/onboarding/initialiser-catalogues",
        json={
            "cylindres_developpes_mm": [314.2],
            "machines_codes": [],
            "matieres_codes": [],
            "options_codes": [],
        },
    )
    assert r.status_code == 422
    assert "314.2" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Isolation tenant — user B peut onboarder même si user A l'a déjà fait
# ---------------------------------------------------------------------------


def test_isolation_tenant_onboarding_independants(
    cleanup_tenant_rows, switch_to_user_b
):
    # User A (admin demo, entreprise_id=1) s'onboarde — 96 dents = 304.8 mm
    r = client.post(
        "/api/onboarding/initialiser-catalogues",
        json={
            "cylindres_developpes_mm": [304.8],
            "machines_codes": ["mark_andy_2200"],
            "matieres_codes": [],
            "options_codes": [],
        },
    )
    assert r.status_code == 201

    # On bascule sur user B (entreprise_id=2)
    switch_to_user_b()
    r = client.get("/api/onboarding/status")
    # User B n'a pas encore onboardé — son catalogue est vide
    assert r.json() == {"catalogue_initialise": False}

    # User B peut s'onboarder normalement — 104 dents = 330.2 mm
    r = client.post(
        "/api/onboarding/initialiser-catalogues",
        json={
            "cylindres_developpes_mm": [330.2],
            "machines_codes": ["nilpeter_fa_22"],
            "matieres_codes": [],
            "options_codes": [],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["cylindres"] == 1
    assert body["machines"] == 1
    assert body["baremes"] == 4

    # Vérif DB : les rows sont bien scopées
    db = SessionLocal()
    try:
        assert db.query(CylindreMagnetique).filter_by(entreprise_id=1).count() == 1
        assert db.query(CylindreMagnetique).filter_by(entreprise_id=2).count() == 1
        assert (
            db.query(MachineImprimerie).filter_by(entreprise_id=1).first().nom
            == "Mark Andy 2200"
        )
        assert (
            db.query(MachineImprimerie).filter_by(entreprise_id=2).first().nom
            == "Nilpeter FA-22"
        )
    finally:
        db.close()
