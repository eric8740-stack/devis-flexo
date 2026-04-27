from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import charge_mensuelle as crud
from app.db import get_db
from app.schemas.charge_mensuelle import (
    ChargeMensuelleCreate,
    ChargeMensuelleRead,
    ChargeMensuelleUpdate,
)

router = APIRouter(prefix="/api/charges-mensuelles", tags=["charges-mensuelles"])


@router.get("", response_model=list[ChargeMensuelleRead])
def list_charges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_charges(db, skip=skip, limit=limit)


@router.get("/{charge_id}", response_model=ChargeMensuelleRead)
def get_charge(charge_id: int, db: Session = Depends(get_db)):
    c = crud.get_charge(db, charge_id)
    if c is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChargeMensuelle {charge_id} introuvable",
        )
    return c


@router.post(
    "",
    response_model=ChargeMensuelleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_charge(
    data: ChargeMensuelleCreate, db: Session = Depends(get_db)
):
    return crud.create_charge(db, data)


@router.put("/{charge_id}", response_model=ChargeMensuelleRead)
def update_charge(
    charge_id: int,
    data: ChargeMensuelleUpdate,
    db: Session = Depends(get_db),
):
    c = crud.update_charge(db, charge_id, data)
    if c is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChargeMensuelle {charge_id} introuvable",
        )
    return c


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_charge(charge_id: int, db: Session = Depends(get_db)):
    if not crud.delete_charge(db, charge_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChargeMensuelle {charge_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
