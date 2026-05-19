"""Tests API /api/cylindres (Brief #29 commit 2)."""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique

client = TestClient(app)


def _purge_cylindres():
    """Vide la table cylindre_magnetique pour isoler les tests."""
    with SessionLocal() as db:
        db.query(CylindreMagnetique).delete()
        db.commit()


def test_cylindre_crud_complet():
    """Cycle complet : create → list → get → update → delete (soft) →
    toggle-actif. Vérifie la conversion nb_dents ↔ developpe_mm."""
    _purge_cylindres()

    # CREATE — nb_dents 104 → developpe_mm = 104 × 3.175 = 330.20
    r = client.post(
        "/api/cylindres",
        json={"nb_dents": 104, "notes": "Test API"},
    )
    assert r.status_code == 201, r.text
    cyl = r.json()
    assert cyl["nb_dents"] == 104
    assert float(cyl["developpe_mm"]) == 330.20
    assert cyl["actif"] is True
    cyl_id = cyl["id"]

    # LIST
    r = client.get("/api/cylindres")
    assert r.status_code == 200
    assert any(c["id"] == cyl_id for c in r.json())

    # GET
    r = client.get(f"/api/cylindres/{cyl_id}")
    assert r.status_code == 200
    assert r.json()["nb_dents"] == 104

    # UPDATE — change nb_dents → developpe_mm recalculé
    r = client.patch(f"/api/cylindres/{cyl_id}", json={"nb_dents": 132})
    assert r.status_code == 200
    assert r.json()["nb_dents"] == 132
    assert float(r.json()["developpe_mm"]) == 419.10  # 132 × 3.175

    # DELETE (soft)
    r = client.delete(f"/api/cylindres/{cyl_id}")
    assert r.status_code == 204
    r = client.get("/api/cylindres")
    assert all(c["id"] != cyl_id for c in r.json())

    # TOGGLE → réactive
    r = client.post(f"/api/cylindres/{cyl_id}/toggle-actif")
    assert r.status_code == 200
    assert r.json()["actif"] is True


def test_cylindre_multi_tenant_strict(switch_to_user_b):
    """User entreprise B ne voit pas les cylindres de l'entreprise A."""
    _purge_cylindres()

    # Tenant A (admin) crée un cyl
    r = client.post("/api/cylindres", json={"nb_dents": 104})
    assert r.status_code == 201
    cyl_a_id = r.json()["id"]

    switch_to_user_b()

    # User B : liste vide (ou sans le cyl A)
    r = client.get("/api/cylindres")
    assert r.status_code == 200
    assert all(c["id"] != cyl_a_id for c in r.json())

    # Accès direct → 404
    r = client.get(f"/api/cylindres/{cyl_a_id}")
    assert r.status_code == 404


def test_cylindre_soft_delete_preserve_row():
    """Soft delete : DELETE → actif=False, row préservée pour FK
    historiques (devis sauvegardés sur ce cyl, lots_production)."""
    _purge_cylindres()

    r = client.post("/api/cylindres", json={"nb_dents": 96})
    cyl_id = r.json()["id"]

    r = client.delete(f"/api/cylindres/{cyl_id}")
    assert r.status_code == 204

    # Row toujours en DB
    with SessionLocal() as db:
        cyl = db.get(CylindreMagnetique, cyl_id)
        assert cyl is not None
        assert cyl.actif is False
        # FK historique préservée (developpe_mm intact). 96 × 3.175 = 304.8.
        assert float(cyl.developpe_mm) == 304.80


def test_cylindre_validation_nb_dents_bornes():
    """Bornes 20 ≤ nb_dents ≤ 300 (flexo standard)."""
    # Sous-borne
    r = client.post("/api/cylindres", json={"nb_dents": 10})
    assert r.status_code == 422
    # Sur-borne
    r = client.post("/api/cylindres", json={"nb_dents": 500})
    assert r.status_code == 422
    # Limite basse OK
    _purge_cylindres()
    r = client.post("/api/cylindres", json={"nb_dents": 20})
    assert r.status_code == 201
    # Limite haute OK
    r = client.post("/api/cylindres", json={"nb_dents": 300})
    assert r.status_code == 201


def test_cylindre_conversion_nb_dents_developpe_mm():
    """La conversion à l'insert utilise DENTS_TO_MM = 3.175 mm/dent,
    arrondie à 2 décimales (Numeric(6, 2))."""
    _purge_cylindres()
    # Note arrondi banker's rounding (Decimal.quantize ROUND_HALF_EVEN) :
    # 593.725 → 593.72 (le 2 est pair, on ne monte pas).
    cas = [
        (80, 254.00),
        (104, 330.20),
        (132, 419.10),
        (187, 593.72),
    ]
    for dents, mm_attendu in cas:
        r = client.post("/api/cylindres", json={"nb_dents": dents})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["nb_dents"] == dents
        assert float(body["developpe_mm"]) == mm_attendu, (
            f"{dents} dents → attendu {mm_attendu} mm, obtenu {body['developpe_mm']}"
        )
