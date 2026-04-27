from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_charges_returns_seeded_6():
    response = client.get("/api/charges-mensuelles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    # Total mensuel attendu : 1800+8000+650+280+420+250 = 11400 €
    total = sum(float(c["montant_eur"]) for c in data)
    assert abs(total - 11400.0) < 0.01


def test_create_charge_returns_201():
    payload = {
        "libelle": "Loyer atelier",
        "categorie": "loyer",
        "montant_eur": 1800.00,
        "date_debut": "2026-01-01",
    }
    response = client.post("/api/charges-mensuelles", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["libelle"] == "Loyer atelier"
    assert data["categorie"] == "loyer"
    assert float(data["montant_eur"]) == 1800.00
    assert data["date_fin"] is None  # en cours


def test_get_charge_existing_returns_200():
    created = client.post(
        "/api/charges-mensuelles",
        json={
            "libelle": "Salaires",
            "categorie": "salaires",
            "montant_eur": 8000.0,
            "date_debut": "2026-01-01",
        },
    ).json()
    response = client.get(f"/api/charges-mensuelles/{created['id']}")
    assert response.status_code == 200
    assert response.json()["categorie"] == "salaires"


def test_get_charge_missing_returns_404():
    response = client.get("/api/charges-mensuelles/9999")
    assert response.status_code == 404


def test_update_charge_modifies_field():
    created = client.post(
        "/api/charges-mensuelles",
        json={
            "libelle": "Énergie",
            "categorie": "energie",
            "montant_eur": 600.0,
            "date_debut": "2026-01-01",
        },
    ).json()
    response = client.put(
        f"/api/charges-mensuelles/{created['id']}",
        json={"montant_eur": 750.0, "date_fin": "2026-12-31"},
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["montant_eur"]) == 750.0
    assert data["date_fin"] == "2026-12-31"


def test_delete_charge_returns_204():
    created = client.post(
        "/api/charges-mensuelles",
        json={
            "libelle": "À zapper",
            "categorie": "autre",
            "montant_eur": 50.0,
            "date_debut": "2026-01-01",
        },
    ).json()
    response = client.delete(f"/api/charges-mensuelles/{created['id']}")
    assert response.status_code == 204


def test_create_charge_invalid_categorie_returns_422():
    response = client.post(
        "/api/charges-mensuelles",
        json={
            "libelle": "X",
            "categorie": "n_importe_quoi",
            "montant_eur": 100.0,
            "date_debut": "2026-01-01",
        },
    )
    assert response.status_code == 422
