from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import entreprise as crud
from app.db import get_db
from app.schemas.entreprise import EntrepriseRead, EntrepriseUpdate

router = APIRouter(prefix="/api/entreprise", tags=["entreprise"])


@router.get("", response_model=EntrepriseRead)
def read_entreprise(db: Session = Depends(get_db)):
    entreprise = crud.get_entreprise(db)
    if entreprise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entreprise introuvable (singleton non initialisé)",
        )
    return entreprise


@router.put("", response_model=EntrepriseRead)
def update_entreprise(data: EntrepriseUpdate, db: Session = Depends(get_db)):
    entreprise = crud.update_entreprise(db, data)
    if entreprise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entreprise introuvable (singleton non initialisé)",
        )
    return entreprise
