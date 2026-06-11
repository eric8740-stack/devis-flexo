"""Module Stock S1 back — modèle Bobine + CRUD (granularité A).

Couvre : création scopée + pré-remplissage épaisseur depuis la matière,
emplacement calculé "A.0.25", ml_restant éditable (ml_initial figé), isolation
tenant (B ne voit pas les bobines de A, 404 cross-tenant), suppression scopée,
404 anti-énumération, matière hors périmètre refusée à la création.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _matiere_id(epaisseur: int | None = 90) -> int:
    """1ère matière du tenant démo, épaisseur fixée pour des assertions stables."""
    _onboard_if_needed()
    with SessionLocal() as db:
        m = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        m.epaisseur_microns = epaisseur
        db.commit()
        return m.id


def _payload(mat_id: int, **extra) -> dict:
    base = {
        "matiere_id": mat_id,
        "laize_mm": 330,
        "ml_initial": 2000,
        "rangee": "A",
        "etage": 0,
        "position": 25,
    }
    base.update(extra)
    return base


def _create(mat_id: int, **extra) -> dict:
    r = client.post("/api/bobines", json=_payload(mat_id, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def test_create_scopee_prefill_epaisseur_et_ml_restant():
    mat_id = _matiere_id(epaisseur=90)
    b = _create(mat_id)
    assert b["matiere_id"] == mat_id
    assert b["epaisseur_microns"] == 90  # pré-rempli depuis la matière
    assert b["ml_initial"] == 2000
    assert b["ml_restant"] == 2000  # = ml_initial à la création
    assert b["statut"] == "en_stock"  # défaut


def test_epaisseur_explicite_prime_sur_matiere():
    mat_id = _matiere_id(epaisseur=90)
    b = _create(mat_id, epaisseur_microns=120)
    assert b["epaisseur_microns"] == 120


def test_emplacement_calcule():
    mat_id = _matiere_id()
    b = _create(mat_id, rangee="A", etage=0, position=25)
    assert b["emplacement"] == "A.0.25"


def test_ml_restant_editable_ml_initial_fige():
    mat_id = _matiere_id()
    b = _create(mat_id)
    r = client.patch(f"/api/bobines/{b['id']}", json={"ml_restant": 1500})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["ml_restant"] == 1500
    assert out["ml_initial"] == 2000  # figé (non modifiable)


def test_suppression_scopee():
    mat_id = _matiere_id()
    b = _create(mat_id)
    assert client.delete(f"/api/bobines/{b['id']}").status_code == 204
    assert client.get(f"/api/bobines/{b['id']}").status_code == 404


def test_404_anti_enumeration():
    assert client.get("/api/bobines/999999").status_code == 404
    assert client.patch("/api/bobines/999999", json={"ml_restant": 1}).status_code == 404
    assert client.delete("/api/bobines/999999").status_code == 404


def test_post_matiere_hors_perimetre_404():
    r = client.post("/api/bobines", json=_payload(999999))
    assert r.status_code == 404


def test_isolation_tenant_liste_vide(switch_to_user_b):
    """B ne voit aucune bobine de A (liste scopée vide)."""
    mat_id = _matiere_id()
    _create(mat_id)  # créée par A (admin démo)
    switch_to_user_b()  # bascule B (entreprise_id=2)
    r = client.get("/api/bobines")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_cross_tenant_404(switch_to_user_b):
    """B ne peut ni lire ni supprimer une bobine de A (404 anti-énumération)."""
    mat_id = _matiere_id()
    b = _create(mat_id)  # créée par A (admin démo)
    switch_to_user_b()
    assert client.get(f"/api/bobines/{b['id']}").status_code == 404
    assert client.delete(f"/api/bobines/{b['id']}").status_code == 404
    assert client.patch(
        f"/api/bobines/{b['id']}", json={"ml_restant": 1}
    ).status_code == 404
