"""Router /api/entreprise — Sprint 12-C scoped.

Singleton-like par user : 1 user = 1 entreprise (D2 brief Sprint 12).
Le user accède uniquement à SA entreprise (lue via user.entreprise_id).
Pas de POST/DELETE — création via /api/auth/register, suppression via
/api/admin/users (S12-D).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import entreprise as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.entreprise import EntrepriseRead, EntrepriseUpdate

router = APIRouter(prefix="/api/entreprise", tags=["entreprise"])


@router.get("", response_model=EntrepriseRead)
def read_entreprise(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Renvoie l'entreprise du user authentifié."""
    entreprise = crud.get_entreprise_by_id(db, user.entreprise_id)
    if entreprise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entreprise du user introuvable (incohérence FK)",
        )
    return entreprise


@router.put("", response_model=EntrepriseRead)
def update_entreprise(
    data: EntrepriseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Modifie l'entreprise du user authentifié."""
    entreprise = crud.update_entreprise_by_id(db, user.entreprise_id, data)
    if entreprise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entreprise du user introuvable",
        )
    return entreprise
