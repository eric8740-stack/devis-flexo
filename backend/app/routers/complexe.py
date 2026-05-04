"""Router /api/complexes — Sprint 12-C scoped + soft delete (S9 v2 conservé)."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import complexe as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Complexe, User
from app.schemas.complexe import ComplexeCreate, ComplexeRead, ComplexeUpdate
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/complexes", tags=["complexes"])


@router.get("", response_model=list[ComplexeRead])
def list_complexes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_inactives: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(db.query(Complexe), Complexe, user)
    if not include_inactives:
        query = query.filter(Complexe.actif.is_(True))
    return query.order_by(Complexe.id).offset(skip).limit(limit).all()


@router.get("/{complexe_id}", response_model=ComplexeRead)
def get_complexe(
    complexe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, Complexe, complexe_id, user)


@router.post(
    "", response_model=ComplexeRead, status_code=status.HTTP_201_CREATED
)
def create_complexe(
    data: ComplexeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_complexe(db, data, entreprise_id=user.entreprise_id)


@router.put("/{complexe_id}", response_model=ComplexeRead)
def update_complexe(
    complexe_id: int,
    data: ComplexeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Complexe, complexe_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{complexe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complexe(
    complexe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sprint 9 v2 — soft delete (`actif=False`). Sprint 12-C — scope user."""
    item = get_or_404_scoped(db, Complexe, complexe_id, user)
    item.actif = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{complexe_id}/reactiver", response_model=ComplexeRead)
def reactiver_complexe(
    complexe_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Complexe, complexe_id, user)
    item.actif = True
    db.commit()
    db.refresh(item)
    return item
