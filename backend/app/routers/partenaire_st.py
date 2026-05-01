from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import partenaire_st as crud
from app.db import get_db
from app.schemas.partenaire_st import (
    PartenaireSTCreate,
    PartenaireSTRead,
    PartenaireSTUpdate,
)

router = APIRouter(prefix="/api/partenaires-st", tags=["partenaires-st"])


@router.get("", response_model=list[PartenaireSTRead])
def list_partenaires(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_inactives: bool = Query(False),
    db: Session = Depends(get_db),
):
    return crud.list_partenaires(
        db, skip=skip, limit=limit, include_inactives=include_inactives
    )


@router.get("/{partenaire_id}", response_model=PartenaireSTRead)
def get_partenaire(partenaire_id: int, db: Session = Depends(get_db)):
    p = crud.get_partenaire(db, partenaire_id)
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PartenaireST {partenaire_id} introuvable",
        )
    return p


@router.post(
    "", response_model=PartenaireSTRead, status_code=status.HTTP_201_CREATED
)
def create_partenaire(data: PartenaireSTCreate, db: Session = Depends(get_db)):
    return crud.create_partenaire(db, data)


@router.put("/{partenaire_id}", response_model=PartenaireSTRead)
def update_partenaire(
    partenaire_id: int,
    data: PartenaireSTUpdate,
    db: Session = Depends(get_db),
):
    p = crud.update_partenaire(db, partenaire_id, data)
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PartenaireST {partenaire_id} introuvable",
        )
    return p


@router.delete("/{partenaire_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partenaire(partenaire_id: int, db: Session = Depends(get_db)):
    """Sprint 9 v2 — soft delete (passe `actif=False`)."""
    if not crud.delete_partenaire(db, partenaire_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PartenaireST {partenaire_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{partenaire_id}/reactiver", response_model=PartenaireSTRead)
def reactiver_partenaire(partenaire_id: int, db: Session = Depends(get_db)):
    if not crud.reactiver_partenaire(db, partenaire_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PartenaireST {partenaire_id} introuvable",
        )
    return crud.get_partenaire(db, partenaire_id)
