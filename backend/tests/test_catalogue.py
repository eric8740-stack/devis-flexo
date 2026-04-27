from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_catalogue_returns_seeded_5():
    response = client.get("/api/catalogue")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["client_id"] == 1
    assert data[0]["code_produit"] == "VIN_75CL_2025"


def test_create_catalogue_returns_201_with_client_seede():
    """client_id=1 = Château des Vignes du Haut-Limousin (seedé)."""
    payload = {
        "code_produit": "ETIQ_75CL_2025",
        "designation": "Étiquette bouteille 75cl millésime 2025",
        "client_id": 1,
        "matiere": "Couché mat 90g",
        "format_mm": "60x80",
        "nb_couleurs": 4,
        "prix_unitaire_eur": 0.085,
        "frequence_estimee": "annuelle",
    }
    response = client.post("/api/catalogue", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code_produit"] == "ETIQ_75CL_2025"
    assert data["client_id"] == 1
    assert data["statut"] == "actif"


def test_get_catalogue_existing_returns_200():
    created = client.post(
        "/api/catalogue",
        json={
            "code_produit": "TEST_001",
            "designation": "Produit test",
            "client_id": 2,
        },
    ).json()
    response = client.get(f"/api/catalogue/{created['id']}")
    assert response.status_code == 200
    assert response.json()["client_id"] == 2


def test_get_catalogue_missing_returns_404():
    response = client.get("/api/catalogue/9999")
    assert response.status_code == 404


def test_update_catalogue_modifies_prix():
    created = client.post(
        "/api/catalogue",
        json={
            "code_produit": "MAJ_001",
            "designation": "Pour MAJ",
            "client_id": 3,
            "prix_unitaire_eur": 0.10,
        },
    ).json()
    response = client.put(
        f"/api/catalogue/{created['id']}", json={"prix_unitaire_eur": 0.12}
    )
    assert response.status_code == 200
    assert float(response.json()["prix_unitaire_eur"]) == 0.12


def test_delete_catalogue_returns_204():
    created = client.post(
        "/api/catalogue",
        json={
            "code_produit": "ZAP",
            "designation": "À supprimer",
            "client_id": 1,
        },
    ).json()
    response = client.delete(f"/api/catalogue/{created['id']}")
    assert response.status_code == 204


def test_filter_catalogue_by_client_id():
    """GET /api/catalogue?client_id=X renvoie uniquement les produits du client X."""
    client.post(
        "/api/catalogue",
        json={"code_produit": "C5_A", "designation": "p1", "client_id": 5},
    )
    client.post(
        "/api/catalogue",
        json={"code_produit": "C5_B", "designation": "p2", "client_id": 5},
    )
    client.post(
        "/api/catalogue",
        json={"code_produit": "C7_X", "designation": "p3", "client_id": 7},
    )

    response = client.get("/api/catalogue?client_id=5")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all(it["client_id"] == 5 for it in items)


def test_create_catalogue_unique_constraint_code_client():
    """code_produit + client_id doit être unique → 409 Conflict via exception handler."""
    first = client.post(
        "/api/catalogue",
        json={"code_produit": "DUP", "designation": "1er", "client_id": 1},
    )
    assert first.status_code == 201

    response = client.post(
        "/api/catalogue",
        json={"code_produit": "DUP", "designation": "2eme", "client_id": 1},
    )
    assert response.status_code == 409
    assert "intégrité" in response.json()["detail"].lower()
