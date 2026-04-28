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
