from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import complexe as crud
from app.db import get_db
from app.schemas.complexe import ComplexeCreate, ComplexeRead, ComplexeUpdate

router = APIRouter(prefix="/api/complexes", tags=["complexes"])


@router.get("", response_model=list[ComplexeRead])
def list_complexes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_complexes(db, skip=skip, limit=limit)


@router.get("/{complexe_id}", response_model=ComplexeRead)
def get_complexe(complexe_id: int, db: Session = Depends(get_db)):
    c = crud.get_complexe(db, complexe_id)
    if c is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complexe {complexe_id} introuvable",
        )
    return c


@router.post(
    "", response_model=ComplexeRead, status_code=status.HTTP_201_CREATED
)
def create_complexe(data: ComplexeCreate, db: Session = Depends(get_db)):
    return crud.create_complexe(db, data)


@router.put("/{complexe_id}", response_model=ComplexeRead)
def update_complexe(
    complexe_id: int, data: ComplexeUpdate, db: Session = Depends(get_db)
):
    c = crud.update_complexe(db, complexe_id, data)
    if c is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complexe {complexe_id} introuvable",
        )
    return c


@router.delete("/{complexe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complexe(complexe_id: int, db: Session = Depends(get_db)):
    if not crud.delete_complexe(db, complexe_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complexe {complexe_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
