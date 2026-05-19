"""Tests modèle PorteCliche (Brief #29 commit 1)."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import PorteCliche


def test_creation_porte_cliche():
    """Création basique d'un porte-cliché et vérif persistance."""
    with SessionLocal() as db:
        pc = PorteCliche(
            entreprise_id=1,
            reference="TEST-PC-001",
            marque="TestMarque",
            laize_utile_mm=250.50,
            diametre_interieur_mm=76,
            matiere="polyuréthane",
            actif=True,
        )
        db.add(pc)
        db.commit()
        db.refresh(pc)
        assert pc.id is not None
        assert pc.reference == "TEST-PC-001"
        assert pc.marque == "TestMarque"
        assert float(pc.laize_utile_mm) == 250.50
        assert pc.actif is True


def test_unique_ref_par_entreprise():
    """UniqueConstraint(entreprise_id, reference) : 2 porte-clichés avec
    même ref dans la même entreprise → IntegrityError."""
    with SessionLocal() as db:
        pc1 = PorteCliche(
            entreprise_id=1,
            reference="UNIQ-TEST",
            laize_utile_mm=200,
        )
        db.add(pc1)
        db.commit()

        pc2 = PorteCliche(
            entreprise_id=1,
            reference="UNIQ-TEST",  # même ref
            laize_utile_mm=300,
        )
        db.add(pc2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_soft_delete_via_actif_false():
    """Soft delete : passer actif=False préserve la row en DB
    (cohérent avec convention Sprint 9 v2 + brief #29)."""
    with SessionLocal() as db:
        pc = PorteCliche(
            entreprise_id=1,
            reference="SOFT-DEL-TEST",
            laize_utile_mm=180,
            actif=True,
        )
        db.add(pc)
        db.commit()
        pc_id = pc.id

        # Soft delete
        pc.actif = False
        db.commit()

        # Toujours en DB
        reloaded = db.get(PorteCliche, pc_id)
        assert reloaded is not None
        assert reloaded.actif is False
        assert reloaded.reference == "SOFT-DEL-TEST"
