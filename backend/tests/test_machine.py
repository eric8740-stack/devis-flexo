from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_machines_returns_seeded_3():
    response = client.get("/api/machines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["nom"] == "Mark Andy P5"


# Sprint 7 Lot 7a — laize_max_mm requis dans MachineCreate
# (consommé par le matcher cylindres pour la contrainte largeur plaque)
_DEFAULT_LAIZE = 330


def test_create_machine_returns_201():
    payload = {
        "nom": "TEST Press Unique",
        "largeur_max_mm": 330,
        "laize_max_mm": _DEFAULT_LAIZE,
        "vitesse_max_m_min": 200,
        "nb_couleurs": 8,
        "cout_horaire_eur": 60.0,
        "actif": True,
    }
    response = client.post("/api/machines", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 3
    assert data["nom"] == "TEST Press Unique"
    assert data["nb_couleurs"] == 8
    assert data["actif"] is True
    assert float(data["laize_max_mm"]) == 330
    assert "date_creation" in data
    assert "date_maj" in data


def test_create_machine_duplicate_nom_returns_409():
    """UNIQUE sur nom → IntegrityError convertie en 409 par le handler global."""
    response = client.post(
        "/api/machines",
        json={"nom": "Mark Andy P5", "laize_max_mm": _DEFAULT_LAIZE},
    )
    assert response.status_code == 409


def test_create_machine_missing_laize_returns_422():
    """Sprint 7 — laize_max_mm est requis Pydantic."""
    response = client.post(
        "/api/machines",
        json={"nom": "Sans laize", "largeur_max_mm": 330},
    )
    assert response.status_code == 422


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
        "/api/machines",
        json={"nom": "Test Press", "nb_couleurs": 4, "laize_max_mm": _DEFAULT_LAIZE},
    ).json()
    response = client.put(
        f"/api/machines/{created['id']}",
        json={"nb_couleurs": 6, "actif": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nb_couleurs"] == 6
    assert data["actif"] is False
    assert data["nom"] == "Test Press"  # non touché


def test_delete_machine_soft_delete_then_reactiver():
    """Sprint 9 v2 — DELETE = soft delete (`actif=False`).

    La machine reste consultable via GET /id, disparaît de la liste par
    défaut (filtre actif=True), réapparaît avec ?include_inactives=true,
    et peut être réactivée via POST /id/reactiver.
    """
    created = client.post(
        "/api/machines",
        json={"nom": "À supprimer", "laize_max_mm": _DEFAULT_LAIZE},
    ).json()
    machine_id = created["id"]

    # DELETE soft : 204, le record existe toujours en BDD
    response = client.delete(f"/api/machines/{machine_id}")
    assert response.status_code == 204

    # GET individuel reste accessible (utile pour la modale de réactivation)
    response = client.get(f"/api/machines/{machine_id}")
    assert response.status_code == 200
    assert response.json()["actif"] is False

    # Liste par défaut filtre actif=True → la machine n'apparaît plus
    listed_ids = [m["id"] for m in client.get("/api/machines").json()]
    assert machine_id not in listed_ids

    # Liste include_inactives=true → la machine apparaît avec actif=False
    listed_with_inactives = client.get("/api/machines?include_inactives=true").json()
    inactif = next(m for m in listed_with_inactives if m["id"] == machine_id)
    assert inactif["actif"] is False

    # Réactivation : 200, actif=True, réapparaît dans la liste par défaut
    response = client.post(f"/api/machines/{machine_id}/reactiver")
    assert response.status_code == 200
    assert response.json()["actif"] is True
    listed_ids = [m["id"] for m in client.get("/api/machines").json()]
    assert machine_id in listed_ids


def test_reactiver_machine_missing_returns_404():
    response = client.post("/api/machines/9999/reactiver")
    assert response.status_code == 404


def test_create_machine_invalid_actif_returns_422():
    """Sprint 9 v2 : `actif` est Boolean strict, une string non-coercible
    déclenche une 422 Pydantic."""
    response = client.post(
        "/api/machines",
        json={"nom": "X", "laize_max_mm": _DEFAULT_LAIZE, "actif": "n_importe_quoi"},
    )
    assert response.status_code == 422


def test_seeded_machine_exposes_calc_params():
    """Mark Andy P5 doit exposer les paramètres calcul S3 (vitesse moyenne
    réaliste de prod et durée de calage), distincts de la vitesse_max_m_min
    catalogue."""
    response = client.get("/api/machines/1")
    data = response.json()
    assert data["vitesse_moyenne_m_h"] == 6000
    assert float(data["duree_calage_h"]) == 1.00
    # vitesse_max_m_min reste exposée et différente (200 m/min = 12000 m/h pic)
    assert data["vitesse_max_m_min"] == 200
    # Sprint 7 Lot 7a — laize machine pour matcher cylindres
    assert float(data["laize_max_mm"]) == 330.0


def test_update_machine_calc_params():
    response = client.put(
        "/api/machines/1",
        json={"vitesse_moyenne_m_h": 5500, "duree_calage_h": 0.60},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vitesse_moyenne_m_h"] == 5500
    assert float(data["duree_calage_h"]) == 0.60
