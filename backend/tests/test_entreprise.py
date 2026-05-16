from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_entreprise_returns_seeded_data():
    response = client.get("/api/entreprise")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["raison_sociale"] == "Paysant & Fils Étiquettes"
    assert data["siret"] == "12345678901234"
    assert data["pct_fg"] == 0.08
    assert data["pct_marge_defaut"] == 0.18
    assert data["heures_prod_presse_mois"] == 130
    assert data["heures_prod_finition_mois"] == 140


def test_put_entreprise_modifies_field_and_persists():
    response = client.put(
        "/api/entreprise",
        json={
            "raison_sociale": "Paysant & Fils Étiquettes",
            "email": "nouveau@paysant-fils.fr",
        },
    )
    assert response.status_code == 200
    assert response.json()["email"] == "nouveau@paysant-fils.fr"

    # GET re-confirme la persistance
    response = client.get("/api/entreprise")
    assert response.json()["email"] == "nouveau@paysant-fils.fr"


def test_put_entreprise_partial_update_keeps_other_fields():
    """exclude_unset : les champs non fournis ne sont PAS écrasés."""
    response = client.put(
        "/api/entreprise",
        json={
            "raison_sociale": "Paysant & Fils Étiquettes",
            "email": "test@example.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Champs absents du body : valeurs d'origine conservées
    assert data["siret"] == "12345678901234"
    assert data["pct_fg"] == 0.08
    assert data["heures_prod_presse_mois"] == 130


def test_put_entreprise_requires_raison_sociale():
    response = client.put(
        "/api/entreprise",
        json={"email": "x@y.fr"},  # raison_sociale manquant
    )
    assert response.status_code == 422  # Pydantic validation error


def test_put_entreprise_updates_numeric_fields():
    response = client.put(
        "/api/entreprise",
        json={
            "raison_sociale": "Paysant & Fils Étiquettes",
            "pct_fg": 0.10,
            "heures_prod_presse_mois": 150,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pct_fg"] == 0.10
    assert data["heures_prod_presse_mois"] == 150


# ---------------------------------------------------------------------------
# PR #9.1 — paramètres BAT (Bon À Tirer)
# ---------------------------------------------------------------------------


def test_get_entreprise_expose_defaults_bat():
    """Tout tenant freshly seedé porte les 4 defaults BAT ICE."""
    response = client.get("/api/entreprise")
    assert response.status_code == 200
    data = response.json()
    assert data["chute_laterale_min_mm"] == "10.00"
    assert data["palier_laize_papier_mm"] == 10
    assert data["refilage_systematique"] is False
    assert data["marge_liner_mm"] == "2.50"


def test_put_entreprise_modifie_params_bat():
    """Le tenant peut ajuster ses 4 paramètres BAT via PUT."""
    response = client.put(
        "/api/entreprise",
        json={
            "raison_sociale": "Paysant & Fils Étiquettes",
            "chute_laterale_min_mm": "12.50",
            "palier_laize_papier_mm": 5,
            "refilage_systematique": True,
            "marge_liner_mm": "3.00",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["chute_laterale_min_mm"] == "12.50"
    assert data["palier_laize_papier_mm"] == 5
    assert data["refilage_systematique"] is True
    assert data["marge_liner_mm"] == "3.00"


def test_put_entreprise_borne_chute_laterale_rejette_negative():
    response = client.put(
        "/api/entreprise",
        json={
            "raison_sociale": "Paysant & Fils Étiquettes",
            "chute_laterale_min_mm": "-1.00",
        },
    )
    assert response.status_code == 422


def test_put_entreprise_borne_palier_rejette_zero():
    """palier_laize_papier_mm doit être >= 1 (0 = division par zéro côté calcul)."""
    response = client.put(
        "/api/entreprise",
        json={
            "raison_sociale": "Paysant & Fils Étiquettes",
            "palier_laize_papier_mm": 0,
        },
    )
    assert response.status_code == 422
