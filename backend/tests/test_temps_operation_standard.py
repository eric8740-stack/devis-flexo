from decimal import Decimal

from app.crud.temps_operation_standard import (
    create_temps_operation,
    list_temps_operations,
    update_temps_operation,
)
from app.db import SessionLocal
from app.models import TempsOperationStandard
from app.schemas.temps_operation_standard import (
    TempsOperationStandardCreate,
    TempsOperationStandardUpdate,
)


def test_seed_loads_15_operations_in_order():
    with SessionLocal() as db:
        ops = list_temps_operations(db)
    assert len(ops) == 15
    # ordre_affichage strictement croissant 1..15
    assert [o.ordre_affichage for o in ops] == list(range(1, 16))
    # 1ère opération attendue
    assert ops[0].libelle_operation == "Retournement de laize"
    assert ops[0].minutes_standard == Decimal("5.00")


def test_create_temps_operation_persists():
    payload = TempsOperationStandardCreate(
        libelle_operation="Test op spéciale",
        minutes_standard=Decimal("12.50"),
        categorie="calage",
        ordre_affichage=99,
    )
    with SessionLocal() as db:
        created = create_temps_operation(db, payload, entreprise_id=1)
        assert created.id is not None
        assert created.actif is True


def test_update_temps_operation_modifies_minutes():
    with SessionLocal() as db:
        op = (
            db.query(TempsOperationStandard)
            .filter(TempsOperationStandard.libelle_operation == "Recherche couleur")
            .first()
        )
        updated = update_temps_operation(
            db, op.id, TempsOperationStandardUpdate(minutes_standard=Decimal("8.00"))
        )
    assert updated.minutes_standard == Decimal("8.00")
