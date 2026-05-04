from sqlalchemy.orm import Session

from app.models import ChargeMensuelle
from app.schemas.charge_mensuelle import (
    ChargeMensuelleCreate,
    ChargeMensuelleUpdate,
)


def list_charges(
    db: Session, skip: int = 0, limit: int = 50
) -> list[ChargeMensuelle]:
    return (
        db.query(ChargeMensuelle)
        .order_by(ChargeMensuelle.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_charge(db: Session, charge_id: int) -> ChargeMensuelle | None:
    return (
        db.query(ChargeMensuelle)
        .filter(ChargeMensuelle.id == charge_id)
        .first()
    )


def create_charge(
    db: Session, data: ChargeMensuelleCreate, entreprise_id: int
) -> ChargeMensuelle:
    """S12-C : `entreprise_id` injecté par le router via user.entreprise_id."""
    c = ChargeMensuelle(entreprise_id=entreprise_id, **data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_charge(
    db: Session, charge_id: int, data: ChargeMensuelleUpdate
) -> ChargeMensuelle | None:
    c = get_charge(db, charge_id)
    if c is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


def delete_charge(db: Session, charge_id: int) -> bool:
    c = get_charge(db, charge_id)
    if c is None:
        return False
    db.delete(c)
    db.commit()
    return True
