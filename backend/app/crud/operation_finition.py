from sqlalchemy.orm import Session

from app.models import OperationFinition
from app.schemas.operation_finition import (
    OperationFinitionCreate,
    OperationFinitionUpdate,
)


def list_operations(
    db: Session, skip: int = 0, limit: int = 50
) -> list[OperationFinition]:
    return (
        db.query(OperationFinition)
        .order_by(OperationFinition.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_operation(db: Session, op_id: int) -> OperationFinition | None:
    return (
        db.query(OperationFinition)
        .filter(OperationFinition.id == op_id)
        .first()
    )


def create_operation(
    db: Session, data: OperationFinitionCreate, entreprise_id: int
) -> OperationFinition:
    """S12-C : `entreprise_id` injecté par le router via user.entreprise_id."""
    op = OperationFinition(entreprise_id=entreprise_id, **data.model_dump())
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def update_operation(
    db: Session, op_id: int, data: OperationFinitionUpdate
) -> OperationFinition | None:
    op = get_operation(db, op_id)
    if op is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(op, field, value)
    db.commit()
    db.refresh(op)
    return op


def delete_operation(db: Session, op_id: int) -> bool:
    op = get_operation(db, op_id)
    if op is None:
        return False
    db.delete(op)
    db.commit()
    return True
