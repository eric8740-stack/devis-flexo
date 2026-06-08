"""Lot back B addendum — persistance du flag « mode sans outil » au POST /devis.

Vérifie que :
  - un POST /api/devis multi-lots SANS cylindre (mode sans outil) ne 422 plus ;
  - le devis rechargé (GET) conserve `mode_sans_outil` + `laize_stock_mm` ;
  - un lot AVEC outil reste `mode_sans_outil=False` (non-régression).
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique, Machine, Matiere, Devis
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _ids() -> tuple[int, int, int]:
    _onboard_if_needed()
    with SessionLocal() as db:
        db.query(Devis).filter_by(entreprise_id=1).delete()
        db.commit()
        m = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True, type_machine="presse")
            .order_by(Machine.id)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        return m.id, mat.id, cyl.id


def _payload(lot: dict) -> dict:
    return {
        "payload_input": {
            "machine_id": lot["machine_id"],
            "format_etiquette_largeur_mm": 50,
            "format_etiquette_hauteur_mm": 40,
            "mode_calcul": "manuel",
        },
        "payload_output": {"mode": "manuel", "prix_vente_ht_eur": "0.00"},
        "statut": "brouillon",
        "quantite_totale": lot["quantite"],
        "lots": [lot],
    }


def test_post_devis_sans_outil_ne_422_plus_et_conserve_le_flag():
    machine_id, mat_id, _ = _ids()
    lot = {
        # cylindre_id OMIS volontairement (lot sans outil).
        "machine_id": machine_id,
        "nb_poses_dev": 1,
        "nb_poses_laize": 1,
        "sens_enroulement": 1,
        "quantite": 10_000,
        "matiere_id": mat_id,
        "mode_sans_outil": True,
        "laize_stock_mm": "250.00",
    }
    r = client.post("/api/devis", json=_payload(lot))
    assert r.status_code == 201, r.text
    devis_id = r.json()["id"]

    # Reload : le flag + la laize stock survivent.
    g = client.get(f"/api/devis/{devis_id}")
    assert g.status_code == 200, g.text
    lots = g.json()["lots_production"]
    assert len(lots) == 1
    assert lots[0]["mode_sans_outil"] is True
    assert lots[0]["laize_stock_mm"] in ("250.00", "250.0", "250")
    assert lots[0]["cylindre_id"] is None


def test_post_devis_avec_outil_flag_false_non_regression():
    machine_id, mat_id, cyl_id = _ids()
    lot = {
        "cylindre_id": cyl_id,
        "machine_id": machine_id,
        "nb_poses_dev": 2,
        "nb_poses_laize": 3,
        "sens_enroulement": 1,
        "quantite": 10_000,
        "matiere_id": mat_id,
    }
    r = client.post("/api/devis", json=_payload(lot))
    assert r.status_code == 201, r.text
    g = client.get(f"/api/devis/{r.json()['id']}")
    assert g.status_code == 200
    lots = g.json()["lots_production"]
    assert lots[0]["mode_sans_outil"] is False
    assert lots[0]["laize_stock_mm"] is None
    assert lots[0]["cylindre_id"] == cyl_id
