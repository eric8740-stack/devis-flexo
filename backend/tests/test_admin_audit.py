"""Tests endpoint admin_audit temporaire (à supprimer avec le router)."""
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_audit_db_seeds_admin_default_returns_200():
    """L'override autouse seed_db_before_each_test connecte l'admin demo
    (is_admin=True). L'endpoint doit donc renvoyer la structure attendue."""
    r = client.get("/api/admin/audit/db-seeds")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "cylindres" in data
    assert "options" in data
    assert "matieres_count" in data
    assert "counts" in data
    assert isinstance(data["cylindres"], list)
    assert isinstance(data["options"], list)
    assert isinstance(data["matieres_count"], int)


def test_audit_db_seeds_non_admin_returns_403(as_user_flexocompare_only):
    """User non-admin (is_admin=False) → 403."""
    r = client.get("/api/admin/audit/db-seeds")
    assert r.status_code == 403
    assert "admin" in r.json()["detail"].lower()
