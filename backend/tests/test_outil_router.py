"""Tests intégration HTTP de GET /api/outils (S5 Lot 5b)."""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import OutilDecoupe

client = TestClient(app)


def test_list_outils_returns_4_seeded():
    response = client.get("/api/outils")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    libelles = {o["libelle"] for o in data}
    assert libelles == {
        "outil_60x40_3p1d",
        "outil_80x50_2p1d",
        "outil_30x20_6p2d",
        "outil_100x70_2p1d_forme",
    }


def test_list_outils_response_contains_format_fields():
    """Schéma OutilDecoupeRead expose tous les champs nécessaires au frontend."""
    response = client.get("/api/outils")
    data = response.json()
    outil = next(o for o in data if o["libelle"] == "outil_60x40_3p1d")
    assert outil["format_l_mm"] == 60
    assert outil["format_h_mm"] == 40
    assert outil["nb_poses_l"] == 3
    assert outil["nb_poses_h"] == 1
    assert outil["forme_speciale"] is False
    assert outil["actif"] is True
    assert "date_creation" in outil
    assert "id" in outil


def test_list_outils_excludes_inactive():
    """Crée un outil inactif et vérifie qu'il n'apparaît pas dans /api/outils."""
    with SessionLocal() as db:
        db.add(
            OutilDecoupe(
                libelle="outil_router_test_inactif",
                format_l_mm=40,
                format_h_mm=30,
                nb_poses_l=4,
                nb_poses_h=1,
                forme_speciale=False,
                actif=False,
            )
        )
        db.commit()

    response = client.get("/api/outils")
    data = response.json()
    assert len(data) == 4  # 4 seedés actifs uniquement
    assert "outil_router_test_inactif" not in {o["libelle"] for o in data}


# Sprint 9 v2 Lot 9d — CRUD complet outil_decoupe (combler le gap)


def test_list_outils_include_inactives_returns_all():
    """`?include_inactives=true` retourne actifs + inactifs."""
    with SessionLocal() as db:
        db.add(
            OutilDecoupe(
                libelle="outil_router_test_inactif_v2",
                format_l_mm=40,
                format_h_mm=30,
                nb_poses_l=4,
                nb_poses_h=1,
                forme_speciale=False,
                actif=False,
            )
        )
        db.commit()

    response = client.get("/api/outils?include_inactives=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5  # 4 seedés actifs + 1 inactif
    assert "outil_router_test_inactif_v2" in {o["libelle"] for o in data}


def test_get_outil_individual_returns_200():
    response = client.get("/api/outils/1")
    assert response.status_code == 200
    assert response.json()["libelle"] == "outil_60x40_3p1d"


def test_get_outil_missing_returns_404():
    response = client.get("/api/outils/9999")
    assert response.status_code == 404


def test_create_outil_returns_201():
    payload = {
        "libelle": "outil_test_s9_50x30",
        "format_l_mm": 50,
        "format_h_mm": 30,
        "nb_poses_l": 4,
        "nb_poses_h": 2,
        "forme_speciale": False,
    }
    response = client.post("/api/outils", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["libelle"] == "outil_test_s9_50x30"
    assert data["actif"] is True
    assert data["id"] > 4


def test_create_outil_duplicate_libelle_returns_409():
    """libelle est UNIQUE → IntegrityError convertie en 409."""
    response = client.post(
        "/api/outils",
        json={
            "libelle": "outil_60x40_3p1d",  # déjà seedé
            "format_l_mm": 60,
            "format_h_mm": 40,
            "nb_poses_l": 3,
            "nb_poses_h": 1,
        },
    )
    assert response.status_code == 409


def test_update_outil_modifies_field():
    response = client.put(
        "/api/outils/1", json={"libelle": "outil_60x40_3p1d_renomme"}
    )
    assert response.status_code == 200
    assert response.json()["libelle"] == "outil_60x40_3p1d_renomme"


def test_update_outil_missing_returns_404():
    response = client.put("/api/outils/9999", json={"libelle": "X"})
    assert response.status_code == 404


def test_delete_outil_soft_then_reactiver():
    """Sprint 9 v2 — DELETE = soft delete, le record reste consultable."""
    response = client.delete("/api/outils/1")
    assert response.status_code == 204

    # Le record reste accessible via GET id, marqué inactif
    response = client.get("/api/outils/1")
    assert response.status_code == 200
    assert response.json()["actif"] is False

    # Liste par défaut filtre actif=True → l'outil n'apparaît plus
    listed = client.get("/api/outils").json()
    assert 1 not in [o["id"] for o in listed]
    assert len(listed) == 3  # 4 seedés - 1 désactivé

    # Liste include_inactives=true le contient
    listed = client.get("/api/outils?include_inactives=true").json()
    assert 1 in [o["id"] for o in listed]

    # Réactivation
    response = client.post("/api/outils/1/reactiver")
    assert response.status_code == 200
    assert response.json()["actif"] is True


def test_delete_outil_missing_returns_404():
    response = client.delete("/api/outils/9999")
    assert response.status_code == 404


def test_reactiver_outil_missing_returns_404():
    response = client.post("/api/outils/9999/reactiver")
    assert response.status_code == 404
