"""Router /api/charges-mensuelles — Sprint 12-C scoped."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import charge_mensuelle as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import ChargeMensuelle, User
from app.schemas.charge_mensuelle import (
    ChargeMensuelleCreate,
    ChargeMensuelleRead,
    ChargeMensuelleUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/charges-mensuelles", tags=["charges-mensuelles"])


@router.get("", response_model=list[ChargeMensuelleRead])
def list_charges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(
        db.query(ChargeMensuelle), ChargeMensuelle, user
    )
    return query.order_by(ChargeMensuelle.id).offset(skip).limit(limit).all()


@router.get("/{charge_id}", response_model=ChargeMensuelleRead)
def get_charge(
    charge_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, ChargeMensuelle, charge_id, user)


@router.post(
    "",
    response_model=ChargeMensuelleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_charge(
    data: ChargeMensuelleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_charge(db, data, entreprise_id=user.entreprise_id)


@router.put("/{charge_id}", response_model=ChargeMensuelleRead)
def update_charge(
    charge_id: int,
    data: ChargeMensuelleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, ChargeMensuelle, charge_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_charge(
    charge_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, ChargeMensuelle, charge_id, user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
