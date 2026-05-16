"""Tests du router /api/parametres/options-fabrication.

Couvre :
  - GET list : ne renvoie QUE les options tenant (pas le catalogue global)
  - POST from-master : 201 + valeur_recommandee_origine snapshotée
  - POST from-master : 404 si code inconnu
  - POST from-master : 409 si déjà activé
  - PATCH : update coefs/prix/actif sans toucher à valeur_recommandee_origine
  - PATCH : 404 sur option d'un autre tenant
  - DELETE : soft delete (actif=False), row reste en base
  - 403 si user n'a pas le module flexocompare
  - Isolation tenant cross-A/B
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import OptionFabrication


client = TestClient(app)

BASE = "/api/parametres/options-fabrication"


@pytest.fixture
def clean_options():
    """Vide option_fabrication pour les tenants test avant + après."""
    db: Session = SessionLocal()
    try:
        for ent_id in (1, 2, 3, 4):
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
        db.commit()
        yield
        for ent_id in (1, 2, 3, 4):
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET list
# ---------------------------------------------------------------------------


def test_list_renvoie_uniquement_options_tenant(clean_options):
    """Une option globale (entreprise_id=NULL) ne doit PAS apparaître ici
    (c'est l'écran d'édition tenant, pas la liste consommable du moteur)."""
    db: Session = SessionLocal()
    try:
        db.add(
            OptionFabrication(
                entreprise_id=None,
                code="opt_globale_only",
                libelle="Option globale",
                categorie="Test",
                actif=True,
            )
        )
        db.add(
            OptionFabrication(
                entreprise_id=1,
                code="opt_tenant_1",
                libelle="Option tenant 1",
                categorie="Test",
                actif=True,
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get(BASE)
    assert r.status_code == 200, r.text
    codes = {o["code"] for o in r.json()}
    assert "opt_tenant_1" in codes
    assert "opt_globale_only" not in codes


# ---------------------------------------------------------------------------
# POST from-master
# ---------------------------------------------------------------------------


def test_post_from_master_active_et_snapshot_recommande(clean_options):
    r = client.post(f"{BASE}/from-master/vernis_selectif")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"] == "vernis_selectif"
    assert body["libelle"] == "Vernis sélectif"
    assert body["actif"] is True
    # Le snapshot porte les coefs catalogue Sprint 13 (cf. catalogue_defaults.py)
    rec = body["valeur_recommandee_origine"]
    assert rec is not None
    assert pytest.approx(float(rec["coef_vitesse_impact"]), abs=1e-6) == 0.95
    assert pytest.approx(float(rec["coef_gache_impact"]), abs=1e-6) == 1.03


def test_post_from_master_404_si_code_inconnu(clean_options):
    r = client.post(f"{BASE}/from-master/option_qui_nexiste_pas")
    assert r.status_code == 404
    assert "option_qui_nexiste_pas" in r.json()["detail"]


def test_post_from_master_409_si_deja_active(clean_options):
    r1 = client.post(f"{BASE}/from-master/vernis_selectif")
    assert r1.status_code == 201
    r2 = client.post(f"{BASE}/from-master/vernis_selectif")
    assert r2.status_code == 409
    assert "déjà activée" in r2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------


def test_patch_update_coefs_et_actif(clean_options):
    created = client.post(f"{BASE}/from-master/vernis_selectif").json()
    option_id = created["id"]
    snapshot_avant = created["valeur_recommandee_origine"]

    r = client.patch(
        f"{BASE}/{option_id}",
        json={
            "coef_vitesse_impact": "0.85",
            "coef_gache_impact": "1.10",
            "forfait_eur": "50.00",
            "actif": True,
        },
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert Decimal(updated["coef_vitesse_impact"]) == Decimal("0.85")
    assert Decimal(updated["coef_gache_impact"]) == Decimal("1.10")
    assert Decimal(updated["forfait_eur"]) == Decimal("50.00")
    # Le snapshot recommandé ne doit JAMAIS être modifié par un PATCH
    assert updated["valeur_recommandee_origine"] == snapshot_avant


def test_patch_404_si_option_autre_tenant(clean_options, switch_to_user_b):
    """User A crée une option. User B doit recevoir 404 sur PATCH (anti-énumération)."""
    created = client.post(f"{BASE}/from-master/vernis_selectif").json()
    option_id = created["id"]

    switch_to_user_b()
    r = client.patch(
        f"{BASE}/{option_id}", json={"coef_vitesse_impact": "0.50"}
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


def test_delete_est_soft_delete(clean_options):
    created = client.post(f"{BASE}/from-master/vernis_selectif").json()
    option_id = created["id"]

    r = client.delete(f"{BASE}/{option_id}")
    assert r.status_code == 200, r.text
    assert r.json()["actif"] is False

    # La row reste en BDD
    db: Session = SessionLocal()
    try:
        row = (
            db.query(OptionFabrication)
            .filter_by(id=option_id)
            .first()
        )
        assert row is not None
        assert row.actif is False
    finally:
        db.close()


def test_delete_404_si_option_autre_tenant(clean_options, switch_to_user_b):
    created = client.post(f"{BASE}/from-master/vernis_selectif").json()
    option_id = created["id"]

    switch_to_user_b()
    r = client.delete(f"{BASE}/{option_id}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Isolation tenant + permissions
# ---------------------------------------------------------------------------


def test_list_isolation_tenant_a_invisible_pour_b(
    clean_options, switch_to_user_b
):
    client.post(f"{BASE}/from-master/vernis_selectif")  # tenant 1
    switch_to_user_b()
    r = client.get(BASE)
    assert r.status_code == 200
    codes = {o["code"] for o in r.json()}
    assert "vernis_selectif" not in codes


def test_get_list_403_si_pas_module_flexocompare(
    clean_options, as_user_flexocheck_only
):
    r = client.get(BASE)
    assert r.status_code == 403
    assert "flexocompare" in r.json()["detail"].lower()
