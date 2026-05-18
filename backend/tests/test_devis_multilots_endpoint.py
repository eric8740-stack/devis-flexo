"""Tests endpoint POST /api/devis avec payload multi-lots (Sprint 13 avenant PR B).

Couvre :
  - POST /api/devis avec 2 lots + quantite_totale OK → 201, lots persistés.
  - POST /api/devis avec Σ qté lots != quantite_totale → 422.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis, LotProduction
from tests.test_lot_production_model import _get_fk_ids, _onboard_if_needed

client = TestClient(app)


def _payload_devis_base() -> dict:
    """payload_input + payload_output minimal valide pour /api/devis."""
    return {
        "payload_input": {
            "machine_id": 1,
            "format_etiquette_hauteur_mm": 40,
            "format_etiquette_largeur_mm": 60,
            "mode_calcul": "manuel",
        },
        "payload_output": {"prix_vente_ht_eur": "0", "mode": "manuel"},
    }


def test_post_devis_avec_2_lots():
    """POST avec 2 lots + quantite_totale 15000 → 201, 2 LotProduction créés."""
    _onboard_if_needed()
    with SessionLocal() as db:
        # Clean éventuels devis pour faciliter l'assertion.
        db.query(Devis).delete()
        db.commit()
        cyl_id, mach_id, mat_id = _get_fk_ids(db)

    payload = _payload_devis_base()
    payload["payload_input"]["machine_id"] = mach_id
    payload["quantite_totale"] = 15000
    payload["lots"] = [
        {
            "cylindre_id": cyl_id,
            "machine_id": mach_id,
            "nb_poses_dev": 2,
            "nb_poses_laize": 3,
            "sens_enroulement": 1,
            "quantite": 10000,
            "matiere_id": mat_id,
        },
        {
            "cylindre_id": cyl_id,
            "machine_id": mach_id,
            "nb_poses_dev": 2,
            "nb_poses_laize": 2,
            "sens_enroulement": 1,
            "quantite": 5000,
            "matiere_id": mat_id,
        },
    ]

    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["lots_production"]) == 2
    assert body["lots_production"][0]["ordre"] == 1
    assert body["lots_production"][0]["quantite"] == 10000
    assert body["lots_production"][1]["ordre"] == 2
    assert body["lots_production"][1]["quantite"] == 5000

    # Persisté en DB
    with SessionLocal() as db:
        nb = db.query(LotProduction).filter_by(devis_id=body["id"]).count()
        assert nb == 2


def test_validation_somme_quantites_egale_total():
    """Σ qté lots != quantite_totale → Pydantic rejette en 422."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)

    payload = _payload_devis_base()
    payload["payload_input"]["machine_id"] = mach_id
    payload["quantite_totale"] = 1000  # mais somme lots = 600 + 300 = 900
    payload["lots"] = [
        {
            "cylindre_id": cyl_id,
            "machine_id": mach_id,
            "nb_poses_dev": 1,
            "nb_poses_laize": 1,
            "sens_enroulement": 1,
            "quantite": 600,
            "matiere_id": mat_id,
        },
        {
            "cylindre_id": cyl_id,
            "machine_id": mach_id,
            "nb_poses_dev": 1,
            "nb_poses_laize": 1,
            "sens_enroulement": 2,
            "quantite": 300,
            "matiere_id": mat_id,
        },
    ]
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 422, r.text
