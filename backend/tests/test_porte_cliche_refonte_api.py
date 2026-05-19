"""Tests API /api/porte-cliches refondue (Brief #30 commit 4)."""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import (
    CylindreMagnetique,
    MachineImprimerie,
    PorteCliche,
)
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _purge_pc_tenant1():
    with SessionLocal() as db:
        db.query(PorteCliche).filter_by(entreprise_id=1).delete()
        db.commit()


def _get_fks_tenant1() -> tuple[int, int]:
    _onboard_if_needed()
    with SessionLocal() as db:
        m = (
            db.query(MachineImprimerie)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        c = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        assert m and c
        return m.id, c.id


def test_crud_nouveau_schema():
    """Cycle create → list → get → update → delete (soft) → toggle."""
    _purge_pc_tenant1()
    machine_id, cyl_id = _get_fks_tenant1()

    # CREATE — quantite fournie explicitement
    r = client.post(
        "/api/porte-cliches",
        json={"machine_id": machine_id, "cylindre_id": cyl_id, "quantite": 6},
    )
    assert r.status_code == 201, r.text
    pc = r.json()
    assert pc["machine_id"] == machine_id
    assert pc["cylindre_id"] == cyl_id
    assert pc["quantite"] == 6
    # Champs joints pour l'UI
    assert "machine_nom" in pc and pc["machine_nom"]
    assert "cylindre_nb_dents" in pc and pc["cylindre_nb_dents"] > 0
    pc_id = pc["id"]

    # LIST
    r = client.get(f"/api/porte-cliches?machine_id={machine_id}")
    assert r.status_code == 200
    assert any(p["id"] == pc_id for p in r.json())

    # GET
    r = client.get(f"/api/porte-cliches/{pc_id}")
    assert r.status_code == 200
    assert r.json()["quantite"] == 6

    # PATCH partiel
    r = client.patch(
        f"/api/porte-cliches/{pc_id}",
        json={"quantite": 10, "notes": "Test refonte"},
    )
    assert r.status_code == 200
    assert r.json()["quantite"] == 10
    assert r.json()["notes"] == "Test refonte"

    # DELETE soft
    r = client.delete(f"/api/porte-cliches/{pc_id}")
    assert r.status_code == 204

    # TOGGLE → réactive
    r = client.post(f"/api/porte-cliches/{pc_id}/toggle-actif")
    assert r.status_code == 200
    assert r.json()["actif"] is True


def test_quantite_default_egale_nb_couleurs_machine():
    """Si `quantite` non fournie au POST → default = machine.nb_groupes_couleurs.

    On prend la première machine du tenant 1 ayant nb_groupes_couleurs
    renseigné (cf migration g8a4f9c2e5b1 qui pose les valeurs canoniques).
    Fallback : si aucune machine avec valeur, on en crée une de test.
    """
    _purge_pc_tenant1()
    _onboard_if_needed()
    with SessionLocal() as db:
        machine = (
            db.query(MachineImprimerie)
            .filter_by(entreprise_id=1, actif=True)
            .filter(MachineImprimerie.nb_groupes_couleurs.isnot(None))
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        assert cyl is not None
        # Si aucune machine n'a nb_groupes_couleurs renseigné, on patch la
        # première machine active pour ce test (n'arrive pas en prod car
        # la migration g8a4f9c2e5b1 garantit les valeurs en compte demo).
        if machine is None:
            machine = (
                db.query(MachineImprimerie)
                .filter_by(entreprise_id=1, actif=True)
                .first()
            )
            assert machine is not None
            machine.nb_groupes_couleurs = 8
            db.commit()
        machine_id, cyl_id = machine.id, cyl.id
        nb_attendu = machine.nb_groupes_couleurs

    r = client.post(
        "/api/porte-cliches",
        json={"machine_id": machine_id, "cylindre_id": cyl_id},
        # pas de quantite → default applicatif
    )
    assert r.status_code == 201, r.text
    assert r.json()["quantite"] == nb_attendu


def test_filter_par_machine_id():
    """Filtre `?machine_id=X` restreint la liste à la machine ciblée."""
    _purge_pc_tenant1()
    machine_id, cyl_id = _get_fks_tenant1()

    # Créer un PC sur cette machine
    r = client.post(
        "/api/porte-cliches",
        json={"machine_id": machine_id, "cylindre_id": cyl_id, "quantite": 8},
    )
    assert r.status_code == 201
    pc_id = r.json()["id"]

    # Liste filtrée : doit contenir le nôtre
    r = client.get(f"/api/porte-cliches?machine_id={machine_id}")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert pc_id in ids
    # Tous les PCs retournés appartiennent bien à cette machine
    assert all(p["machine_id"] == machine_id for p in r.json())


def test_validation_fks_meme_entreprise(switch_to_user_b):
    """User entreprise B tente de créer un PC sur la machine du tenant A
    (qu'il ne connaît pas) → 404 (anti-énumération via get_or_404_scoped)."""
    _purge_pc_tenant1()
    machine_id_a, cyl_id_a = _get_fks_tenant1()

    switch_to_user_b()

    r = client.post(
        "/api/porte-cliches",
        json={"machine_id": machine_id_a, "cylindre_id": cyl_id_a, "quantite": 8},
    )
    # 404 sur la machine d'un autre tenant — get_or_404_scoped
    assert r.status_code == 404
