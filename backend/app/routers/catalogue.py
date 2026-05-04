"""Router /api/catalogue — Sprint 12-C scoped."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import catalogue as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Catalogue, User
from app.schemas.catalogue import CatalogueCreate, CatalogueRead, CatalogueUpdate
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/catalogue", tags=["catalogue"])


@router.get("", response_model=list[CatalogueRead])
def list_catalogue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    client_id: int | None = Query(
        default=None,
        description="Filtre : ne renvoie que les produits du client donné",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(db.query(Catalogue), Catalogue, user)
    if client_id is not None:
        query = query.filter(Catalogue.client_id == client_id)
    return query.order_by(Catalogue.id).offset(skip).limit(limit).all()


@router.get("/{item_id}", response_model=CatalogueRead)
def get_catalogue(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, Catalogue, item_id, user)


@router.post(
    "", response_model=CatalogueRead, status_code=status.HTTP_201_CREATED
)
def create_catalogue(
    data: CatalogueCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_catalogue(db, data, entreprise_id=user.entreprise_id)


@router.put("/{item_id}", response_model=CatalogueRead)
def update_catalogue(
    item_id: int,
    data: CatalogueUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Catalogue, item_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalogue(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Catalogue, item_id, user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
