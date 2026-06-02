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
    Machine,
    Matiere,
)
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _fks_tenant1() -> tuple[int, int, int]:
    """(machine_id, cyl_id, matiere_id) tenant 1 actifs."""
    _onboard_if_needed()
    with SessionLocal() as db:
        machine = (
            db.query(Machine)
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


# ---------------------------------------------------------------------------
# Patch #31 — fix bug 1 plantage POST /api/devis : régression coverage E2E.
#
# Le bug du patch #31 était côté UI (DevisResult crash au redirect), mais
# on consolide la couverture backend pour garantir que le POST /api/devis
# fonctionne en mono-lot (cas le plus fréquent : 1 lot sur qté totale).
# ---------------------------------------------------------------------------


def test_creation_devis_un_seul_lot_e2e():
    """Cas usuel patch #31 : utilisateur sélectionne 1 candidat avec la
    quantité totale entière. POST /api/devis doit créer le devis + 1 lot."""
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
            "nb_lots": 1,
            "mandrin_mm": 76,
        },
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "0.00",
            "note": "Coût à recalculer.",
        },
        "statut": "brouillon",
        "quantite_totale": 10000,
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
        ],
    }
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] > 0
    assert len(body["lots_production"]) == 1
    assert body["lots_production"][0]["quantite"] == 10000
    assert body["lots_production"][0]["matiere_id"] == mat_id

    # Vérif persistance DB
    with SessionLocal() as db:
        lots = db.query(LotProduction).filter_by(devis_id=body["id"]).all()
        assert len(lots) == 1
        assert lots[0].quantite == 10000


def test_creation_devis_deux_lots_repartition_e2e():
    """Patch #31 — 2 lots du MÊME candidat (matière différente par lot)
    avec répartition 60/40 sur la qté totale. Vérifie aussi le cas
    'matière indépendante par lot' (cf brief #28 propriété métier)."""
    machine_id, cyl_id, mat_id = _fks_tenant1()
    # 2e matière pour différencier les lots si possible
    with SessionLocal() as db:
        from app.models import Matiere

        autres = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .filter(Matiere.id != mat_id)
            .all()
        )
        if autres:
            mat_id_2 = autres[0].id
        else:
            # Fallback : créer une 2e matière de test
            mat_b = Matiere(
                entreprise_id=1,
                code="test_pet_50",
                libelle="Test PET blanc 50µ",
                actif=True,
            )
            db.add(mat_b)
            db.commit()
            mat_id_2 = mat_b.id
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
        },
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "0.00",
        },
        "statut": "brouillon",
        "quantite_totale": 10000,
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 6000,
                "matiere_id": mat_id,
            },
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 4000,
                "matiere_id": mat_id_2,  # matière différente du lot 1
            },
        ],
    }
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["lots_production"]) == 2
    matieres_par_lot = sorted(
        lot["matiere_id"] for lot in body["lots_production"]
    )
    assert matieres_par_lot == sorted([mat_id, mat_id_2])
