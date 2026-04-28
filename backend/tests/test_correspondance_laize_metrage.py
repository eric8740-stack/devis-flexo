from app.crud.correspondance_laize_metrage import (
    create_correspondance,
    list_correspondances,
    update_correspondance,
)
from app.db import SessionLocal
from app.models import CorrespondanceLaizeMetrage
from app.schemas.correspondance_laize_metrage import (
    CorrespondanceLaizeMetrageCreate,
    CorrespondanceLaizeMetrageUpdate,
)


def test_seed_loads_33_correspondances_with_formula():
    """Formule métrage = (laize_mm / 10) × 35. 50 → 175, 370 → 1295."""
    with SessionLocal() as db:
        corrs = list_correspondances(db)
    assert len(corrs) == 33
    by_laize = {c.laize_mm: c.metrage_metres for c in corrs}
    assert by_laize[50] == 175
    assert by_laize[200] == 700
    assert by_laize[370] == 1295


def test_create_correspondance_persists():
    payload = CorrespondanceLaizeMetrageCreate(laize_mm=400, metrage_metres=1400)
    with SessionLocal() as db:
        created = create_correspondance(db, payload)
        assert created.id is not None
        assert created.laize_mm == 400


def test_update_correspondance_modifies_metrage():
    with SessionLocal() as db:
        corr = (
            db.query(CorrespondanceLaizeMetrage)
            .filter(CorrespondanceLaizeMetrage.laize_mm == 100)
            .first()
        )
        updated = update_correspondance(
            db, corr.id, CorrespondanceLaizeMetrageUpdate(metrage_metres=360)
        )
    assert updated.metrage_metres == 360
