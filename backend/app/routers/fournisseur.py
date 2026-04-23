from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import fournisseur as crud
from app.db import get_db
from app.schemas.fournisseur import (
    FournisseurCreate,
    FournisseurRead,
    FournisseurUpdate,
)

router = APIRouter(prefix="/api/fournisseurs", tags=["fournisseurs"])


@router.get("", response_model=list[FournisseurRead])
def list_fournisseurs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_fournisseurs(db, skip=skip, limit=limit)


@router.get("/{fournisseur_id}", response_model=FournisseurRead)
def get_fournisseur(fournisseur_id: int, db: Session = Depends(get_db)):
    fournisseur = crud.get_fournisseur(db, fournisseur_id)
    if fournisseur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fournisseur {fournisseur_id} introuvable",
        )
    return fournisseur


@router.post(
    "", response_model=FournisseurRead, status_code=status.HTTP_201_CREATED
)
def create_fournisseur(
    data: FournisseurCreate, db: Session = Depends(get_db)
):
    return crud.create_fournisseur(db, data)


@router.put("/{fournisseur_id}", response_model=FournisseurRead)
def update_fournisseur(
    fournisseur_id: int,
    data: FournisseurUpdate,
    db: Session = Depends(get_db),
):
    fournisseur = crud.update_fournisseur(db, fournisseur_id, data)
    if fournisseur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fournisseur {fournisseur_id} introuvable",
        )
    return fournisseur


@router.delete(
    "/{fournisseur_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_fournisseur(fournisseur_id: int, db: Session = Depends(get_db)):
    if not crud.delete_fournisseur(db, fournisseur_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fournisseur {fournisseur_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
