from sqlalchemy.orm import Session

from app.models import Complexe
from app.schemas.complexe import ComplexeCreate, ComplexeUpdate


def list_complexes(
    db: Session, skip: int = 0, limit: int = 50
) -> list[Complexe]:
    return (
        db.query(Complexe).order_by(Complexe.id).offset(skip).limit(limit).all()
    )


def get_complexe(db: Session, complexe_id: int) -> Complexe | None:
    return db.query(Complexe).filter(Complexe.id == complexe_id).first()


def create_complexe(db: Session, data: ComplexeCreate) -> Complexe:
    c = Complexe(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_complexe(
    db: Session, complexe_id: int, data: ComplexeUpdate
) -> Complexe | None:
    c = get_complexe(db, complexe_id)
    if c is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


def delete_complexe(db: Session, complexe_id: int) -> bool:
    c = get_complexe(db, complexe_id)
    if c is None:
        return False
    db.delete(c)
    db.commit()
    return True
