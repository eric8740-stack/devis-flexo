from sqlalchemy.orm import Session

from app.models import Catalogue
from app.schemas.catalogue import CatalogueCreate, CatalogueUpdate


def list_catalogue(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    client_id: int | None = None,
) -> list[Catalogue]:
    query = db.query(Catalogue).order_by(Catalogue.id)
    if client_id is not None:
        query = query.filter(Catalogue.client_id == client_id)
    return query.offset(skip).limit(limit).all()


def get_catalogue(db: Session, item_id: int) -> Catalogue | None:
    return db.query(Catalogue).filter(Catalogue.id == item_id).first()


def create_catalogue(db: Session, data: CatalogueCreate) -> Catalogue:
    # S12-A : entreprise_id=1 (compte demo). S12-C remplacera par user.entreprise_id
    item = Catalogue(entreprise_id=1, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_catalogue(
    db: Session, item_id: int, data: CatalogueUpdate
) -> Catalogue | None:
    item = get_catalogue(db, item_id)
    if item is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_catalogue(db: Session, item_id: int) -> bool:
    item = get_catalogue(db, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
