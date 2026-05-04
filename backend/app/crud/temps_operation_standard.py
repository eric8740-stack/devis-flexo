from sqlalchemy.orm import Session

from app.models import TempsOperationStandard
from app.schemas.temps_operation_standard import (
    TempsOperationStandardCreate,
    TempsOperationStandardUpdate,
)


def list_temps_operations(
    db: Session, skip: int = 0, limit: int = 50
) -> list[TempsOperationStandard]:
    return (
        db.query(TempsOperationStandard)
        .order_by(TempsOperationStandard.ordre_affichage)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_temps_operation(
    db: Session, temps_id: int
) -> TempsOperationStandard | None:
    return (
        db.query(TempsOperationStandard)
        .filter(TempsOperationStandard.id == temps_id)
        .first()
    )


def create_temps_operation(
    db: Session, data: TempsOperationStandardCreate, entreprise_id: int
) -> TempsOperationStandard:
    """S12-C : `entreprise_id` injecté par le router via user.entreprise_id."""
    temps = TempsOperationStandard(
        entreprise_id=entreprise_id, **data.model_dump()
    )
    db.add(temps)
    db.commit()
    db.refresh(temps)
    return temps


def update_temps_operation(
    db: Session, temps_id: int, data: TempsOperationStandardUpdate
) -> TempsOperationStandard | None:
    temps = get_temps_operation(db, temps_id)
    if temps is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(temps, field, value)
    db.commit()
    db.refresh(temps)
    return temps
