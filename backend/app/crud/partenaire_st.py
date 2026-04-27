from sqlalchemy.orm import Session

from app.models import PartenaireST
from app.schemas.partenaire_st import PartenaireSTCreate, PartenaireSTUpdate


def list_partenaires(
    db: Session, skip: int = 0, limit: int = 50
) -> list[PartenaireST]:
    return (
        db.query(PartenaireST)
        .order_by(PartenaireST.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_partenaire(db: Session, partenaire_id: int) -> PartenaireST | None:
    return (
        db.query(PartenaireST).filter(PartenaireST.id == partenaire_id).first()
    )


def create_partenaire(db: Session, data: PartenaireSTCreate) -> PartenaireST:
    p = PartenaireST(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_partenaire(
    db: Session, partenaire_id: int, data: PartenaireSTUpdate
) -> PartenaireST | None:
    p = get_partenaire(db, partenaire_id)
    if p is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


def delete_partenaire(db: Session, partenaire_id: int) -> bool:
    p = get_partenaire(db, partenaire_id)
    if p is None:
        return False
    db.delete(p)
    db.commit()
    return True
