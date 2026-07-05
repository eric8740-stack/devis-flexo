"""Tests blindage pilote E2 (audit 05/07/2026) — UNIQUE composites tenant.

Migration r7t2u9w4x1z6 : les 8 contraintes UNIQUE globales héritées du
mono-tenant sont passées en composite (entreprise_id, clé).

Couvre :
  - Deux tenants peuvent créer chacun une machine du même nom (plus de
    409 à l'onboarding du 2ᵉ pilote).
  - Le doublon INTRA-tenant reste bloqué (409).
  - tarif_encre : chaque tenant peut posséder son `pantone` (le bug E2
    bloquait la création des tarifs du 2ᵉ tenant → CostEngineError).
  - charge_machine_mensuelle : même (mois, annee) possible sur 2 tenants.
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.main import app
from app.models import ChargeMachineMensuelle, Machine, TarifEncre
from tests.conftest import USER_B_ENTREPRISE_ID

client = TestClient(app)


def _nom_machine_demo() -> str:
    with SessionLocal() as db:
        machine = db.query(Machine).filter_by(entreprise_id=1).first()
        assert machine is not None
        return machine.nom


def test_deux_tenants_peuvent_avoir_la_meme_machine(as_user_b):
    """User B crée une machine portant le nom d'une machine du tenant démo
    → 201 (avant la migration : 409 IntegrityError sur machine.nom)."""
    nom_demo = _nom_machine_demo()

    r = client.post(
        "/api/machines",
        json={"nom": nom_demo, "laize_max_mm": 330},
    )
    assert r.status_code == 201, r.text
    assert r.json()["nom"] == nom_demo

    # Les deux rows coexistent, chacune chez son tenant.
    with SessionLocal() as db:
        assert db.query(Machine).filter_by(nom=nom_demo).count() == 2


def test_doublon_intra_tenant_reste_bloque_409(as_user_b):
    """La contrainte composite continue de bloquer le doublon DANS un
    même tenant (handler IntegrityError → 409)."""
    r = client.post(
        "/api/machines", json={"nom": "Presse Unique B", "laize_max_mm": 330}
    )
    assert r.status_code == 201, r.text

    r = client.post(
        "/api/machines", json={"nom": "Presse Unique B", "laize_max_mm": 330}
    )
    assert r.status_code == 409, r.text


def test_chaque_tenant_peut_posseder_son_tarif_pantone(as_user_b):
    """Le tenant démo possède déjà `pantone` (seed). Le tenant B doit
    pouvoir créer le sien — c'était le blocage CostEngineError du 2ᵉ
    tenant relevé par l'audit."""
    with SessionLocal() as db:
        assert (
            db.query(TarifEncre)
            .filter_by(entreprise_id=1, type_encre="pantone")
            .count()
            == 1
        )
        db.add(
            TarifEncre(
                entreprise_id=USER_B_ENTREPRISE_ID,
                type_encre="pantone",
                libelle="Pantone tenant B",
                prix_kg_defaut=Decimal("21.50"),
            )
        )
        db.commit()  # ne lève plus IntegrityError

        assert db.query(TarifEncre).filter_by(type_encre="pantone").count() == 2

        # Doublon INTRA-tenant B → toujours refusé.
        db.add(
            TarifEncre(
                entreprise_id=USER_B_ENTREPRISE_ID,
                type_encre="pantone",
                libelle="Pantone tenant B bis",
                prix_kg_defaut=Decimal("22.00"),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_charge_machine_meme_mois_sur_deux_tenants(as_user_b):
    """(mois, annee) identique possible chez 2 tenants ; doublon
    intra-tenant toujours bloqué."""
    with SessionLocal() as db:
        charge_demo = (
            db.query(ChargeMachineMensuelle).filter_by(entreprise_id=1).first()
        )
        assert charge_demo is not None, "Seed sans charge machine mensuelle ?"
        db.add(
            ChargeMachineMensuelle(
                entreprise_id=USER_B_ENTREPRISE_ID,
                mois=charge_demo.mois,
                annee=charge_demo.annee,
                montant_total=Decimal("10000.00"),
                heures_disponibles=Decimal("200.00"),
            )
        )
        db.commit()  # ne lève plus IntegrityError

        db.add(
            ChargeMachineMensuelle(
                entreprise_id=USER_B_ENTREPRISE_ID,
                mois=charge_demo.mois,
                annee=charge_demo.annee,
                montant_total=Decimal("9999.00"),
                heures_disponibles=Decimal("100.00"),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
