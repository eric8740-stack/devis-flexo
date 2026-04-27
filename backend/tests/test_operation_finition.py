from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_operations_returns_seeded_5():
    response = client.get("/api/operations-finition")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


def test_create_operation_returns_201():
    payload = {
        "nom": "TEST Op Unique",
        "unite_facturation": "m2",
        "cout_unitaire_eur": 0.45,
        "temps_minutes_unite": 0.10,
    }
    response = client.post("/api/operations-finition", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "TEST Op Unique"
    assert data["unite_facturation"] == "m2"
    assert data["statut"] == "actif"


def test_get_operation_existing_returns_200():
    """Récupère op seedée #1 (Vernis UV brillant)."""
    response = client.get("/api/operations-finition/1")
    assert response.status_code == 200
    assert "Vernis" in response.json()["nom"]


def test_get_operation_missing_returns_404():
    response = client.get("/api/operations-finition/9999")
    assert response.status_code == 404


def test_update_operation_modifies_field():
    created = client.post(
        "/api/operations-finition",
        json={"nom": "Dorure", "unite_facturation": "ml"},
    ).json()
    response = client.put(
        f"/api/operations-finition/{created['id']}",
        json={"cout_unitaire_eur": 1.20},
    )
    assert response.status_code == 200
    assert response.json()["cout_unitaire_eur"] == 1.20


def test_delete_operation_returns_204():
    created = client.post(
        "/api/operations-finition",
        json={"nom": "À zapper", "unite_facturation": "unite"},
    ).json()
    response = client.delete(f"/api/operations-finition/{created['id']}")
    assert response.status_code == 204
    response = client.get(f"/api/operations-finition/{created['id']}")
    assert response.status_code == 404


def test_create_operation_invalid_unite_returns_422():
    response = client.post(
        "/api/operations-finition",
        json={"nom": "X", "unite_facturation": "kg"},
    )
    assert response.status_code == 422
