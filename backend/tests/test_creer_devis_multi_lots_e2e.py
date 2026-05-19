"""Test E2E création devis multi-lots depuis le workflow optim (Brief #30 commit 1).

Reproduit le payload construit par OptimisationPoseDetailLots.handleValider
côté frontend, et vérifie que POST /api/devis crée bien le devis + ses
lots en cascade.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import (
    CylindreMagnetique,
    Devis,
    LotProduction,
    MachineImprimerie,
    Matiere,
)
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _fks_tenant1() -> tuple[int, int, int]:
    """(machine_id, cyl_id, matiere_id) tenant 1 actifs."""
    _onboard_if_needed()
    with SessionLocal() as db:
        machine = (
            db.query(MachineImprimerie)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        assert machine and cyl and mat
        return machine.id, cyl.id, mat.id


def test_post_devis_multi_lots_renvoie_201_et_id():
    """Payload conforme à ce que le bouton 'Valider et créer le devis'
    construit côté UI étape 3. Retourne 201 + DevisDetail avec id."""
    machine_id, cyl_id, mat_id = _fks_tenant1()
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()

    payload = {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
            "source": "optim_multi_lots",
            "nb_lots": 2,
            "mandrin_mm": 76,
        },
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "0.00",
            "note": "Coût à recalculer.",
        },
        "statut": "brouillon",
        "quantite_totale": 15000,
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 10000,
                "matiere_id": mat_id,
            },
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 2,
                "sens_enroulement": 1,
                "quantite": 5000,
                "matiere_id": mat_id,
            },
        ],
    }
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "id" in body
    assert body["id"] > 0
    assert len(body["lots_production"]) == 2

    # Vérif persistance DB
    with SessionLocal() as db:
        lots = db.query(LotProduction).filter_by(devis_id=body["id"]).all()
        assert len(lots) == 2
        assert sorted(lot.quantite for lot in lots) == [5000, 10000]
