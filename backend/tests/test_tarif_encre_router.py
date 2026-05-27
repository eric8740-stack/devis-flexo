"""Tests GET /api/tarif-encre (lecture, onglet Stratégique section Encre)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_tarif_encre_returns_seeded():
    r = client.get("/api/tarif-encre")
    assert r.status_code == 200, r.text
    data = r.json()
    # 5 types d'encre seedés (tarif_encre.csv).
    assert len(data) == 5
    types = {t["type_encre"] for t in data}
    assert "process_cmj" in types
    # Champs clés exposés pour l'UI.
    first = data[0]
    assert "prix_kg_defaut" in first
    assert "ratio_g_m2_couleur" in first


def test_list_tarif_encre_isolation_user_b(as_user_b):
    """User B (entreprise_id=2) n'a aucun tarif encre seedé."""
    r = client.get("/api/tarif-encre")
    assert r.status_code == 200, r.text
    assert r.json() == []
