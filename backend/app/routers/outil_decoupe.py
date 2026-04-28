"""Endpoint HTTP du catalogue des outils de découpe (S5 Lot 5b).

Lecture seule pour l'instant (pas de POST/PUT/DELETE — UI catalogue
reportée Sprint 6+). Utilisé par le frontend Lot 5d pour peupler le
select « Outil existant » dans le formulaire `/devis/nouveau`.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.outil_decoupe import list_outils_decoupe_actifs
from app.db import get_db
from app.schemas.outil_decoupe import OutilDecoupeRead

router = APIRouter(prefix="/api/outils", tags=["outils"])


@router.get("", response_model=list[OutilDecoupeRead])
def list_outils(db: Session = Depends(get_db)):
    """Renvoie les outils de découpe actifs (tri par libellé)."""
    return list_outils_decoupe_actifs(db)
