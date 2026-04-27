from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_machines_empty_initially():
    response = client.get("/api/machines")
    assert response.status_code == 200
    assert response.json() == []


def test_create_machine_returns_201():
    payload = {
        "nom": "Mark Andy P5",
        "largeur_max_mm": 330,
        "vitesse_max_m_min": 200,
        "nb_couleurs": 8,
        "cout_horaire_eur": 60.0,
        "statut": "actif",
    }
    response = client.post("/api/machines", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] >= 1
    assert data["nom"] == "Mark Andy P5"
    assert data["nb_couleurs"] == 8
    assert data["statut"] == "actif"
    assert "date_creation" in data
    assert "date_maj" in data


def test_get_machine_existing_returns_200():
    created = client.post(
        "/api/machines",
        json={"nom": "Daco D250", "vitesse_max_m_min": 80},
    ).json()
    response = client.get(f"/api/machines/{created['id']}")
    assert response.status_code == 200
    assert response.json()["nom"] == "Daco D250"


def test_get_machine_missing_returns_404():
    response = client.get("/api/machines/9999")
    assert response.status_code == 404


def test_update_machine_modifies_field():
    created = client.post(
        "/api/machines", json={"nom": "Test Press", "nb_couleurs": 4}
    ).json()
    response = client.put(
        f"/api/machines/{created['id']}",
        json={"nb_couleurs": 6, "statut": "maintenance"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nb_couleurs"] == 6
    assert data["statut"] == "maintenance"
    assert data["nom"] == "Test Press"  # non touché


def test_delete_machine_returns_204_then_get_404():
    created = client.post("/api/machines", json={"nom": "À supprimer"}).json()
    response = client.delete(f"/api/machines/{created['id']}")
    assert response.status_code == 204
    response = client.get(f"/api/machines/{created['id']}")
    assert response.status_code == 404


def test_create_machine_invalid_statut_returns_422():
    response = client.post(
        "/api/machines",
        json={"nom": "X", "statut": "n_importe_quoi"},
    )
    assert response.status_code == 422
