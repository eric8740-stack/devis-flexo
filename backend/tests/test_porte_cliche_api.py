"""Tests API /api/porte-cliches (Brief #29 commit 3)."""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import PorteCliche

client = TestClient(app)


def _purge_porte_cliches():
    """Vide la table porte_cliche (test isolation — la migration seed
    crée 3 porte-clichés compte demo qui peuvent gêner)."""
    with SessionLocal() as db:
        db.query(PorteCliche).delete()
        db.commit()


def test_porte_cliche_crud_complet():
    """Cycle complet : create → list → get → update → delete (soft) →
    toggle-actif (réactivation)."""
    _purge_porte_cliches()

    # CREATE
    payload = {
        "reference": "API-PC-01",
        "marque": "TestRotec",
        "laize_utile_mm": 220.0,
        "diametre_interieur_mm": 76.0,
        "matiere": "polyuréthane",
    }
    r = client.post("/api/porte-cliches", json=payload)
    assert r.status_code == 201, r.text
    pc = r.json()
    assert pc["reference"] == "API-PC-01"
    assert pc["actif"] is True
    pc_id = pc["id"]

    # LIST (filtre actif=True par défaut, donc on doit voir le nouveau)
    r = client.get("/api/porte-cliches")
    assert r.status_code == 200
    assert any(p["id"] == pc_id for p in r.json())

    # GET
    r = client.get(f"/api/porte-cliches/{pc_id}")
    assert r.status_code == 200
    assert r.json()["reference"] == "API-PC-01"

    # UPDATE partiel
    r = client.patch(
        f"/api/porte-cliches/{pc_id}",
        json={"marque": "TestUpdated", "notes": "Test update"},
    )
    assert r.status_code == 200
    assert r.json()["marque"] == "TestUpdated"
    assert r.json()["notes"] == "Test update"

    # DELETE (soft)
    r = client.delete(f"/api/porte-cliches/{pc_id}")
    assert r.status_code == 204
    # Plus visible en liste actif=True
    r = client.get("/api/porte-cliches")
    assert all(p["id"] != pc_id for p in r.json())
    # Toujours en DB (vu en filtre actif=False)
    r = client.get("/api/porte-cliches?actif=false")
    assert any(p["id"] == pc_id for p in r.json())

    # TOGGLE → réactive
    r = client.post(f"/api/porte-cliches/{pc_id}/toggle-actif")
    assert r.status_code == 200
    assert r.json()["actif"] is True


def test_porte_cliche_multi_tenant_strict(switch_to_user_b):
    """User entreprise B (entreprise_id=2) ne voit pas les porte-clichés
    de l'entreprise A (entreprise_id=1). GET retourne 404, liste vide."""
    _purge_porte_cliches()

    # Tenant A (admin par défaut) crée un porte-cliché
    r = client.post(
        "/api/porte-cliches",
        json={"reference": "PC-A-PRIVE", "laize_utile_mm": 200.0},
    )
    assert r.status_code == 201
    pc_a_id = r.json()["id"]

    # Bascule user B
    switch_to_user_b()

    # User B ne voit PAS le porte-cliché de A dans sa liste
    r = client.get("/api/porte-cliches")
    assert r.status_code == 200
    assert all(p["id"] != pc_a_id for p in r.json())

    # Accès direct au porte-cliché de A → 404 (anti-énumération)
    r = client.get(f"/api/porte-cliches/{pc_a_id}")
    assert r.status_code == 404


def test_porte_cliche_toggle_actif_endpoint():
    """Endpoint dédié /toggle-actif bascule l'état actif/inactif sans
    nécessiter un PATCH complet (UX rapide depuis l'UI cards)."""
    _purge_porte_cliches()
    r = client.post(
        "/api/porte-cliches",
        json={"reference": "TOGGLE-TEST", "laize_utile_mm": 200.0},
    )
    pc_id = r.json()["id"]
    assert r.json()["actif"] is True

    # Toggle 1 : True → False
    r = client.post(f"/api/porte-cliches/{pc_id}/toggle-actif")
    assert r.status_code == 200
    assert r.json()["actif"] is False

    # Toggle 2 : False → True (réactivation)
    r = client.post(f"/api/porte-cliches/{pc_id}/toggle-actif")
    assert r.status_code == 200
    assert r.json()["actif"] is True


def test_porte_cliche_creation_multiple_compte_demo():
    """On peut créer plusieurs porte-clichés indépendants dans le compte
    demo avec des références distinctes (équivalent au seed initial)."""
    _purge_porte_cliches()
    seeds = [
        ("PC-220-T", "Rotec", 220.0, 76.0, "polyuréthane"),
        ("PC-330-T", "DuPont", 330.0, 76.0, "polyuréthane"),
        ("PC-410-T", "Flint", 410.0, 152.0, "carbone"),
    ]
    for ref, marque, laize, diam, mat in seeds:
        r = client.post(
            "/api/porte-cliches",
            json={
                "reference": ref,
                "marque": marque,
                "laize_utile_mm": laize,
                "diametre_interieur_mm": diam,
                "matiere": mat,
            },
        )
        assert r.status_code == 201, r.text

    r = client.get("/api/porte-cliches")
    refs_api = {pc["reference"] for pc in r.json()}
    assert {"PC-220-T", "PC-330-T", "PC-410-T"}.issubset(refs_api)
