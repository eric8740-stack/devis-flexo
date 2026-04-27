from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_machines_returns_seeded_3():
    response = client.get("/api/machines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["nom"] == "Mark Andy P5"


def test_create_machine_returns_201():
    payload = {
        "nom": "TEST Press Unique",
        "largeur_max_mm": 330,
        "vitesse_max_m_min": 200,
        "nb_couleurs": 8,
        "cout_horaire_eur": 60.0,
        "statut": "actif",
    }
    response = client.post("/api/machines", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 3
    assert data["nom"] == "TEST Press Unique"
    assert data["nb_couleurs"] == 8
    assert data["statut"] == "actif"
    assert "date_creation" in data
    assert "date_maj" in data


def test_create_machine_duplicate_nom_returns_409():
    """UNIQUE sur nom → IntegrityError convertie en 409 par le handler global."""
    response = client.post("/api/machines", json={"nom": "Mark Andy P5"})
    assert response.status_code == 409


def test_get_machine_existing_returns_200():
    """Récupère machine seedée #2 (Daco D250 ligne finition)."""
    response = client.get("/api/machines/2")
    assert response.status_code == 200
    assert "Daco" in response.json()["nom"]


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


def test_seeded_machine_exposes_calc_params():
    """Mark Andy P5 doit exposer les paramètres calcul S3 (vitesse moyenne
    réaliste de prod et durée de calage), distincts de la vitesse_max_m_min
    catalogue."""
    response = client.get("/api/machines/1")
    data = response.json()
    assert data["vitesse_moyenne_m_h"] == 6000
    assert float(data["duree_calage_h"]) == 0.50
    # vitesse_max_m_min reste exposée et différente (200 m/min = 12000 m/h pic)
    assert data["vitesse_max_m_min"] == 200


def test_update_machine_calc_params():
    response = client.put(
        "/api/machines/1",
        json={"vitesse_moyenne_m_h": 5500, "duree_calage_h": 0.60},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vitesse_moyenne_m_h"] == 5500
    assert float(data["duree_calage_h"]) == 0.60
