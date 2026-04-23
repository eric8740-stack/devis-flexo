from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_clients_returns_seeded_20():
    response = client.get("/api/clients")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 20
    assert data[0]["id"] == 1
    assert data[0]["raison_sociale"] == "Château des Vignes du Haut-Limousin"


def test_list_clients_pagination():
    response = client.get("/api/clients?skip=5&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    assert data[0]["id"] == 6


def test_get_client_existing_returns_200():
    response = client.get("/api/clients/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["segment"] == "vin"
    assert data["date_creation"] == "2024-03-15"


def test_get_client_missing_returns_404():
    response = client.get("/api/clients/9999")
    assert response.status_code == 404


def test_create_client_returns_201_and_increments_count():
    payload = {
        "raison_sociale": "Test Client SARL",
        "segment": "alimentaire",
        "email": "test@example.fr",
    }
    response = client.post("/api/clients", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["raison_sociale"] == "Test Client SARL"
    assert created["segment"] == "alimentaire"
    assert "id" in created and created["id"] > 20

    # Liste passe à 21
    list_response = client.get("/api/clients?limit=200")
    assert len(list_response.json()) == 21


def test_update_client_modifies_fields():
    response = client.put(
        "/api/clients/1",
        json={"email": "nouveau@chateau-vignes-hl.fr", "tel": "05 55 99 88 77"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "nouveau@chateau-vignes-hl.fr"
    assert data["tel"] == "05 55 99 88 77"
    # Champs non fournis : conservés
    assert data["raison_sociale"] == "Château des Vignes du Haut-Limousin"
    assert data["segment"] == "vin"


def test_update_client_missing_returns_404():
    response = client.put("/api/clients/9999", json={"email": "x@y.fr"})
    assert response.status_code == 404


def test_delete_client_returns_204_then_get_404():
    response = client.delete("/api/clients/1")
    assert response.status_code == 204

    response = client.get("/api/clients/1")
    assert response.status_code == 404


def test_delete_client_missing_returns_404():
    response = client.delete("/api/clients/9999")
    assert response.status_code == 404
