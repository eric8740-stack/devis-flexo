"""Router /api/outils — Sprint 12-C scoped + soft delete (S9 v2 conservé)."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import outil_decoupe as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import OutilDecoupe, User
from app.schemas.outil_decoupe import (
    OutilDecoupeCreate,
    OutilDecoupeRead,
    OutilDecoupeUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/outils", tags=["outils"])


@router.get("", response_model=list[OutilDecoupeRead])
def list_outils(
    include_inactives: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(db.query(OutilDecoupe), OutilDecoupe, user)
    if not include_inactives:
        query = query.filter(OutilDecoupe.actif.is_(True))
    return query.order_by(OutilDecoupe.libelle).all()


@router.get("/{outil_id}", response_model=OutilDecoupeRead)
def get_outil(
    outil_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, OutilDecoupe, outil_id, user)


@router.post(
    "", response_model=OutilDecoupeRead, status_code=status.HTTP_201_CREATED
)
def create_outil(
    data: OutilDecoupeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_outil_decoupe(db, data, entreprise_id=user.entreprise_id)


@router.put("/{outil_id}", response_model=OutilDecoupeRead)
def update_outil(
    outil_id: int,
    data: OutilDecoupeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, OutilDecoupe, outil_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{outil_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_outil(
    outil_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sprint 9 v2 — soft delete (`actif=False`). Sprint 12-C — scope user."""
    item = get_or_404_scoped(db, OutilDecoupe, outil_id, user)
    item.actif = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{outil_id}/reactiver", response_model=OutilDecoupeRead)
def reactiver_outil(
    outil_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, OutilDecoupe, outil_id, user)
    item.actif = True
    db.commit()
    db.refresh(item)
    return item
