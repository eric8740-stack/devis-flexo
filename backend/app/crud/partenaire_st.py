from sqlalchemy.orm import Session

from app.models import PartenaireST
from app.schemas.partenaire_st import PartenaireSTCreate, PartenaireSTUpdate


def list_partenaires(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    include_inactives: bool = False,
) -> list[PartenaireST]:
    """Sprint 9 v2 — `include_inactives=False` (default) filtre actif=True."""
    query = db.query(PartenaireST)
    if not include_inactives:
        query = query.filter(PartenaireST.actif.is_(True))
    return query.order_by(PartenaireST.id).offset(skip).limit(limit).all()


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
    """Sprint 9 v2 — soft delete (passe `actif=False`)."""
    p = get_partenaire(db, partenaire_id)
    if p is None:
        return False
    p.actif = False
    db.commit()
    return True


def reactiver_partenaire(db: Session, partenaire_id: int) -> bool:
    """Sprint 9 v2 — passe `actif=True`."""
    p = get_partenaire(db, partenaire_id)
    if p is None:
        return False
    p.actif = True
    db.commit()
    return True
