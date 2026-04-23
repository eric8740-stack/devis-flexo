from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_fournisseurs_returns_seeded_5():
    response = client.get("/api/fournisseurs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["id"] == 1
    assert data[0]["raison_sociale"] == "Antalis France"


def test_get_fournisseur_existing_returns_200():
    response = client.get("/api/fournisseurs/5")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["raison_sociale"] == "Chesapeake Ink Solutions"
    assert data["categorie"] == "encre_consommable"


def test_get_fournisseur_missing_returns_404():
    response = client.get("/api/fournisseurs/9999")
    assert response.status_code == 404


def test_create_fournisseur_returns_201():
    payload = {
        "raison_sociale": "Nouveau Fournisseur Test",
        "categorie": "complexe_adhesif",
        "delai_livraison_j": 10,
    }
    response = client.post("/api/fournisseurs", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["raison_sociale"] == "Nouveau Fournisseur Test"
    assert created["delai_livraison_j"] == 10
    assert created["id"] > 5


def test_update_fournisseur_modifies_fields():
    response = client.put(
        "/api/fournisseurs/1",
        json={"conditions_paiement": "60 jours nets", "delai_livraison_j": 8},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conditions_paiement"] == "60 jours nets"
    assert data["delai_livraison_j"] == 8
    assert data["raison_sociale"] == "Antalis France"


def test_delete_fournisseur_returns_204_then_get_404():
    response = client.delete("/api/fournisseurs/1")
    assert response.status_code == 204
    response = client.get("/api/fournisseurs/1")
    assert response.status_code == 404


def test_delete_fournisseur_missing_returns_404():
    response = client.delete("/api/fournisseurs/9999")
    assert response.status_code == 404
