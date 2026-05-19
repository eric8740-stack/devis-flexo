"""Tests modèle PorteCliche refondu (Brief #30 commit 3)."""
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    CylindreMagnetique,
    MachineImprimerie,
    PorteCliche,
)
from tests.test_lot_production_model import _onboard_if_needed


def _get_fks_tenant1(db: Session) -> tuple[int, int]:
    """Retourne (machine_id, cylindre_id) pour tenant 1, onboarde si besoin."""
    _onboard_if_needed()
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
    assert machine is not None, "Pas de machine seedée tenant 1"
    assert cyl is not None, "Pas de cylindre seedé tenant 1"
    return machine.id, cyl.id


def _purge_pc_tenant1():
    """Vide les PC tenant 1 — chaque test crée son couple unique."""
    with SessionLocal() as db:
        db.query(PorteCliche).filter_by(entreprise_id=1).delete()
        db.commit()


def test_modele_nouveau_schema_machine_cyl_quantite():
    """Le nouveau modèle PorteCliche persiste machine_id + cylindre_id +
    quantite. Les anciens champs (reference, marque, etc.) n'existent plus."""
    _purge_pc_tenant1()
    with SessionLocal() as db:
        machine_id, cyl_id = _get_fks_tenant1(db)
        pc = PorteCliche(
            entreprise_id=1,
            machine_id=machine_id,
            cylindre_id=cyl_id,
            quantite=8,
        )
        db.add(pc)
        db.commit()
        db.refresh(pc)
        assert pc.id is not None
        assert pc.machine_id == machine_id
        assert pc.cylindre_id == cyl_id
        assert pc.quantite == 8
        assert pc.actif is True
        # Sanity : les anciens champs n'existent plus
        assert not hasattr(pc, "reference")
        assert not hasattr(pc, "marque")
        assert not hasattr(pc, "laize_utile_mm")


def test_unique_constraint_entreprise_machine_cyl():
    """UniqueConstraint(entreprise_id, machine_id, cylindre_id) :
    deux PC sur le même couple → IntegrityError."""
    _purge_pc_tenant1()
    with SessionLocal() as db:
        machine_id, cyl_id = _get_fks_tenant1(db)
        db.add(
            PorteCliche(
                entreprise_id=1,
                machine_id=machine_id,
                cylindre_id=cyl_id,
                quantite=8,
            )
        )
        db.commit()

        db.add(
            PorteCliche(
                entreprise_id=1,
                machine_id=machine_id,  # même machine
                cylindre_id=cyl_id,  # même cyl
                quantite=10,  # différente qté mais peu importe
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_check_constraint_quantite_positive():
    """CheckConstraint(quantite >= 0) : quantite négative → IntegrityError."""
    _purge_pc_tenant1()
    with SessionLocal() as db:
        machine_id, cyl_id = _get_fks_tenant1(db)
        db.add(
            PorteCliche(
                entreprise_id=1,
                machine_id=machine_id,
                cylindre_id=cyl_id,
                quantite=-1,  # invalide
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_soft_delete_via_actif_false():
    """actif=False préserve la row en DB (convention Sprint 9 v2)."""
    _purge_pc_tenant1()
    with SessionLocal() as db:
        machine_id, cyl_id = _get_fks_tenant1(db)
        pc = PorteCliche(
            entreprise_id=1,
            machine_id=machine_id,
            cylindre_id=cyl_id,
            quantite=8,
        )
        db.add(pc)
        db.commit()
        pc_id = pc.id

        pc.actif = False
        db.commit()

        reloaded = db.get(PorteCliche, pc_id)
        assert reloaded is not None
        assert reloaded.actif is False
        assert reloaded.machine_id == machine_id
