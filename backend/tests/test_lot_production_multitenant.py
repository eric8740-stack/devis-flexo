"""Tests isolation multi-tenant pour LotProduction (Sprint 13 avenant).

Couvre :
  - Un lot de A est récupérable via get_or_404_scoped pour user A.
  - User B (entreprise_id=2) reçoit 404 en tentant de lire un lot de A
    (pattern anti-énumération multi-tenant — get_or_404_scoped).
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import LotProduction, User
from app.services.scope_service import get_or_404_scoped
from tests.test_lot_production_model import (
    _create_devis_minimal,
    _get_fk_ids,
    _onboard_if_needed,
)

client = TestClient(app)


def _create_lot_tenant_1() -> int:
    """Crée un lot pour tenant 1 et retourne son id."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)
        devis = _create_devis_minimal(db, numero="MT-TEST-001")
        lot = LotProduction(
            devis_id=devis.id,
            entreprise_id=1,
            ordre=1,
            cylindre_id=cyl_id,
            machine_id=mach_id,
            nb_poses_dev=2,
            nb_poses_laize=3,
            sens_enroulement=1,
            quantite=1000,
            matiere_id=mat_id,
        )
        db.add(lot)
        db.commit()
        return lot.id


def test_lot_scope_entreprise_via_get_or_404_scoped():
    """User A (entreprise_id=1) récupère son propre lot OK via le scope."""
    lot_id = _create_lot_tenant_1()
    with SessionLocal() as db:
        user_a = User(entreprise_id=1, email="a@test.fr", is_active=True)
        # get_or_404_scoped lève HTTPException 404 si scope mismatch.
        lot = get_or_404_scoped(db, LotProduction, lot_id, user_a)
        assert lot.id == lot_id
        assert lot.entreprise_id == 1


def test_user_voit_pas_lots_autre_entreprise():
    """User B (entreprise_id=2) ne peut pas accéder à un lot de tenant 1.
    get_or_404_scoped → HTTPException 404 (pattern anti-énumération).

    On crée le lot pour tenant 1 (auth admin par défaut), puis on simule
    un user B en construisant l'objet directement sans toucher à l'override
    auth (qui forcerait l'onboarding sur tenant 2)."""
    from fastapi import HTTPException

    import pytest as _pytest

    lot_id = _create_lot_tenant_1()
    with SessionLocal() as db:
        user_b = User(entreprise_id=2, email="b@test.fr", is_active=True)
        with _pytest.raises(HTTPException) as exc:
            get_or_404_scoped(db, LotProduction, lot_id, user_b)
        assert exc.value.status_code == 404
