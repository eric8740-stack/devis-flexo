"""Router /api/fournisseurs — Sprint 12-C scoped."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import fournisseur as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Fournisseur, User
from app.schemas.fournisseur import (
    FournisseurCreate,
    FournisseurRead,
    FournisseurUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/fournisseurs", tags=["fournisseurs"])


@router.get("", response_model=list[FournisseurRead])
def list_fournisseurs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(db.query(Fournisseur), Fournisseur, user)
    return query.order_by(Fournisseur.id).offset(skip).limit(limit).all()


@router.get("/{fournisseur_id}", response_model=FournisseurRead)
def get_fournisseur(
    fournisseur_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, Fournisseur, fournisseur_id, user)


@router.post(
    "", response_model=FournisseurRead, status_code=status.HTTP_201_CREATED
)
def create_fournisseur(
    data: FournisseurCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_fournisseur(db, data, entreprise_id=user.entreprise_id)


@router.put("/{fournisseur_id}", response_model=FournisseurRead)
def update_fournisseur(
    fournisseur_id: int,
    data: FournisseurUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Fournisseur, fournisseur_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/{fournisseur_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_fournisseur(
    fournisseur_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Fournisseur, fournisseur_id, user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
