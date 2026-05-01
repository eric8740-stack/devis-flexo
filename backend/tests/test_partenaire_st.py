from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_partenaires_returns_seeded_4():
    response = client.get("/api/partenaires-st")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4


def test_create_partenaire_returns_201():
    payload = {
        "raison_sociale": "Pelliculage Lyonnais",
        "siret": "12345678900011",
        "contact_nom": "M. Durand",
        "contact_email": "contact@pellic-lyon.fr",
        "prestation_type": "finition",
        "delai_jours_moyen": 5,
        "qualite_score": 4,
    }
    response = client.post("/api/partenaires-st", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["raison_sociale"] == "Pelliculage Lyonnais"
    assert data["qualite_score"] == 4
    assert data["actif"] is True


def test_get_partenaire_existing_returns_200():
    created = client.post(
        "/api/partenaires-st",
        json={"raison_sociale": "Dorure SAS", "prestation_type": "dorure"},
    ).json()
    response = client.get(f"/api/partenaires-st/{created['id']}")
    assert response.status_code == 200
    assert response.json()["raison_sociale"] == "Dorure SAS"


def test_get_partenaire_missing_returns_404():
    response = client.get("/api/partenaires-st/9999")
    assert response.status_code == 404


def test_update_partenaire_modifies_field():
    created = client.post(
        "/api/partenaires-st",
        json={"raison_sociale": "Découpe Pro", "qualite_score": 3},
    ).json()
    response = client.put(
        f"/api/partenaires-st/{created['id']}",
        json={"qualite_score": 5, "actif": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["qualite_score"] == 5
    assert data["actif"] is False


def test_delete_partenaire_returns_204():
    created = client.post(
        "/api/partenaires-st", json={"raison_sociale": "À zapper"}
    ).json()
    response = client.delete(f"/api/partenaires-st/{created['id']}")
    assert response.status_code == 204


def test_create_partenaire_invalid_qualite_score_returns_422():
    response = client.post(
        "/api/partenaires-st",
        json={"raison_sociale": "X", "qualite_score": 10},
    )
    assert response.status_code == 422
