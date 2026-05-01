from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_complexes_returns_seeded_31():
    response = client.get("/api/complexes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 31
    # Le complexe COUCHE_MAT_90 (benchmark A du PRD) doit être présent à 1.20 €/m²
    couche_mat = [c for c in data if c["reference"] == "COUCHE_MAT_90"]
    assert len(couche_mat) == 1
    assert float(couche_mat[0]["prix_m2_eur"]) == 1.20


def test_create_complexe_returns_201_with_fournisseur_seede():
    """fournisseur_id=1 = Antalis France (seedé par autouse fixture)."""
    payload = {
        "reference": "BOPP_50_BLANC",
        "famille": "bopp",
        "face_matiere": "BOPP blanc 50µ",
        "prix_m2_eur": 1.45,
        "fournisseur_id": 1,
    }
    response = client.post("/api/complexes", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["reference"] == "BOPP_50_BLANC"
    assert data["famille"] == "bopp"
    assert float(data["prix_m2_eur"]) == 1.45
    assert data["fournisseur_id"] == 1


def test_get_complexe_existing_returns_200():
    created = client.post(
        "/api/complexes",
        json={
            "reference": "PAPIER_COUCHE_MAT_90",
            "famille": "papier_couche",
            "grammage_g_m2": 90,
            "prix_m2_eur": 1.20,
        },
    ).json()
    response = client.get(f"/api/complexes/{created['id']}")
    assert response.status_code == 200
    assert response.json()["grammage_g_m2"] == 90


def test_get_complexe_missing_returns_404():
    response = client.get("/api/complexes/9999")
    assert response.status_code == 404


def test_update_complexe_modifies_prix_m2():
    """prix_m2_eur est CRITIQUE pour le moteur de calcul S3."""
    created = client.post(
        "/api/complexes",
        json={"reference": "PE_70", "famille": "pe", "prix_m2_eur": 1.30},
    ).json()
    response = client.put(
        f"/api/complexes/{created['id']}", json={"prix_m2_eur": 1.55}
    )
    assert response.status_code == 200
    assert float(response.json()["prix_m2_eur"]) == 1.55


def test_delete_complexe_soft_delete_then_reactiver():
    """Sprint 9 v2 — DELETE = soft delete (`actif=False`)."""
    created = client.post(
        "/api/complexes",
        json={"reference": "À_ZAPPER", "famille": "autre", "prix_m2_eur": 0.5},
    )
    # 'autre' n'est pas dans l'enum FamilleComplexe → 422 attendu
    assert created.status_code == 422

    created = client.post(
        "/api/complexes",
        json={"reference": "ZAP_OK", "famille": "pp", "prix_m2_eur": 0.5},
    ).json()
    complexe_id = created["id"]
    response = client.delete(f"/api/complexes/{complexe_id}")
    assert response.status_code == 204

    # Le record existe toujours et est marqué inactif
    response = client.get(f"/api/complexes/{complexe_id}")
    assert response.status_code == 200
    assert response.json()["actif"] is False

    # Réactivation
    response = client.post(f"/api/complexes/{complexe_id}/reactiver")
    assert response.status_code == 200
    assert response.json()["actif"] is True


def test_create_complexe_negative_prix_returns_422():
    response = client.post(
        "/api/complexes",
        json={"reference": "X", "famille": "pp", "prix_m2_eur": -1.0},
    )
    assert response.status_code == 422
