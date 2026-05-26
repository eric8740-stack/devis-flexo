"""Tests endpoint /api/clients — exposition des 9 colonnes profil rebobinage.

Couvre :
  - POST /api/clients accepte les 9 champs et les persiste
  - GET /api/clients/{id} renvoie les 9 champs
  - PUT /api/clients/{id} met à jour les 9 champs (partial update)
  - sens_enroulement bornes 1..8 validées par Pydantic (422 hors plage)
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Client


_http = TestClient(app)


_PAYLOAD_FULL = {
    "raison_sociale": "Test client profil rebobinage API",
    "diametre_mandrin_mm": 76,
    "diametre_max_bobine_mm": 300,
    "sens_enroulement": 1,
    "nb_etiq_par_bobine_fixe": 1000,
    "marquage_bobine_requis": True,
    "marquage_bobine_format": "lot/date/qté",
    "mandrin_fourni_par_client": True,
    "film_protection_requis": True,
    "conditionnement_souhaite": "Palette filmée 80x120",
}


def test_post_clients_accepte_et_renvoie_les_9_champs_rebobinage():
    """POST /api/clients avec les 9 champs → 201 + persist + renvoie tout."""
    r = _http.post("/api/clients", json=_PAYLOAD_FULL)
    assert r.status_code == 201, r.text
    data = r.json()
    # Les 9 champs sont dans la réponse
    assert data["diametre_mandrin_mm"] == 76
    assert data["diametre_max_bobine_mm"] == 300
    assert data["sens_enroulement"] == 1
    assert data["nb_etiq_par_bobine_fixe"] == 1000
    assert data["marquage_bobine_requis"] is True
    assert data["marquage_bobine_format"] == "lot/date/qté"
    assert data["mandrin_fourni_par_client"] is True
    assert data["film_protection_requis"] is True
    assert data["conditionnement_souhaite"] == "Palette filmée 80x120"

    # Vérif persistance DB côté ORM
    with SessionLocal() as db:
        row = db.query(Client).filter_by(id=data["id"]).one()
        assert row.diametre_mandrin_mm == 76
        assert row.marquage_bobine_requis is True
        assert row.conditionnement_souhaite == "Palette filmée 80x120"


def test_post_clients_sans_champs_rebobinage_applique_defaults():
    """POST avec uniquement raison_sociale → les 3 Boolean prennent False,
    les 6 nullable prennent None (defaults Pydantic + ORM + server_default)."""
    r = _http.post(
        "/api/clients",
        json={"raison_sociale": "Test client sans profil rebobinage"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    # 3 Boolean defaultent à False
    assert data["marquage_bobine_requis"] is False
    assert data["mandrin_fourni_par_client"] is False
    assert data["film_protection_requis"] is False
    # 6 nullable defaultent à None
    assert data["diametre_mandrin_mm"] is None
    assert data["diametre_max_bobine_mm"] is None
    assert data["sens_enroulement"] is None
    assert data["nb_etiq_par_bobine_fixe"] is None
    assert data["marquage_bobine_format"] is None
    assert data["conditionnement_souhaite"] is None


def test_get_clients_renvoie_les_9_champs():
    """GET /api/clients et GET /api/clients/{id} incluent les 9 champs."""
    # Création préalable
    r_post = _http.post("/api/clients", json=_PAYLOAD_FULL)
    client_id = r_post.json()["id"]

    # GET item
    r_get = _http.get(f"/api/clients/{client_id}")
    assert r_get.status_code == 200
    data = r_get.json()
    assert data["sens_enroulement"] == 1
    assert data["nb_etiq_par_bobine_fixe"] == 1000

    # GET list — l'item présent expose aussi les champs
    r_list = _http.get("/api/clients?limit=200")
    assert r_list.status_code == 200
    item = next(it for it in r_list.json() if it["id"] == client_id)
    assert item["diametre_mandrin_mm"] == 76
    assert item["mandrin_fourni_par_client"] is True


def test_put_clients_partial_update_des_champs_rebobinage():
    """PUT /api/clients/{id} avec UN SOUS-ENSEMBLE des 9 champs → ne touche
    que les champs transmis (partial update via `exclude_unset`)."""
    r_post = _http.post(
        "/api/clients",
        json={"raison_sociale": "Test PUT partial"},
    )
    client_id = r_post.json()["id"]
    assert r_post.json()["marquage_bobine_requis"] is False  # default

    # Update uniquement 2 champs sur les 9
    r_put = _http.put(
        f"/api/clients/{client_id}",
        json={
            "marquage_bobine_requis": True,
            "diametre_mandrin_mm": 38,
        },
    )
    assert r_put.status_code == 200, r_put.text
    data = r_put.json()
    assert data["marquage_bobine_requis"] is True
    assert data["diametre_mandrin_mm"] == 38
    # Les autres restent à leur valeur initiale
    assert data["mandrin_fourni_par_client"] is False
    assert data["film_protection_requis"] is False
    assert data["sens_enroulement"] is None


def test_post_clients_sens_enroulement_hors_borne_rejete_422():
    """sens_enroulement ∈ [1, 8] (convention SE1-SE8). 0 ou 9 → 422
    Pydantic validation (Field ge=1, le=8)."""
    r = _http.post(
        "/api/clients",
        json={"raison_sociale": "Test sens invalide", "sens_enroulement": 9},
    )
    assert r.status_code == 422

    r2 = _http.post(
        "/api/clients",
        json={"raison_sociale": "Test sens 0", "sens_enroulement": 0},
    )
    assert r2.status_code == 422


def test_post_clients_sens_enroulement_dans_borne_1_a_8_accepte():
    """Garde de plage Field(ge=1, le=8) — toutes les valeurs SE1-SE8
    canoniques sont acceptées (201) et persistées correctement."""
    for sens in (1, 2, 3, 4, 5, 6, 7, 8):
        r = _http.post(
            "/api/clients",
            json={
                "raison_sociale": f"Test sens valide SE{sens}",
                "sens_enroulement": sens,
            },
        )
        assert r.status_code == 201, (
            f"sens_enroulement={sens} aurait dû être accepté, "
            f"reçu {r.status_code}: {r.text}"
        )
        assert r.json()["sens_enroulement"] == sens


def test_put_clients_sens_enroulement_garde_appliquee_au_update():
    """La garde 1..8 s'applique aussi à `ClientUpdate.sens_enroulement`
    (partial update). Tentative de PUT avec sens=12 → 422."""
    r_post = _http.post(
        "/api/clients",
        json={"raison_sociale": "Test PUT sens"},
    )
    client_id = r_post.json()["id"]

    r_put = _http.put(
        f"/api/clients/{client_id}",
        json={"sens_enroulement": 12},
    )
    assert r_put.status_code == 422
