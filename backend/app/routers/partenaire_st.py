"""Router /api/partenaires-st — Sprint 12-C scoped + soft delete."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import partenaire_st as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import PartenaireST, User
from app.schemas.partenaire_st import (
    PartenaireSTCreate,
    PartenaireSTRead,
    PartenaireSTUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/partenaires-st", tags=["partenaires-st"])


@router.get("", response_model=list[PartenaireSTRead])
def list_partenaires(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_inactives: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(db.query(PartenaireST), PartenaireST, user)
    if not include_inactives:
        query = query.filter(PartenaireST.actif.is_(True))
    return query.order_by(PartenaireST.id).offset(skip).limit(limit).all()


@router.get("/{partenaire_id}", response_model=PartenaireSTRead)
def get_partenaire(
    partenaire_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, PartenaireST, partenaire_id, user)


@router.post(
    "", response_model=PartenaireSTRead, status_code=status.HTTP_201_CREATED
)
def create_partenaire(
    data: PartenaireSTCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_partenaire(db, data, entreprise_id=user.entreprise_id)


@router.put("/{partenaire_id}", response_model=PartenaireSTRead)
def update_partenaire(
    partenaire_id: int,
    data: PartenaireSTUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, PartenaireST, partenaire_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{partenaire_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partenaire(
    partenaire_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sprint 9 v2 — soft delete (`actif=False`). Sprint 12-C — scope user."""
    item = get_or_404_scoped(db, PartenaireST, partenaire_id, user)
    item.actif = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{partenaire_id}/reactiver", response_model=PartenaireSTRead)
def reactiver_partenaire(
    partenaire_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, PartenaireST, partenaire_id, user)
    item.actif = True
    db.commit()
    db.refresh(item)
    return item
