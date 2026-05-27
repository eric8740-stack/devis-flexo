"""Router /api/tarif-encre — lecture des tarifs encre (onglet Stratégique).

Brief frontend Stratégique, section 3 (Encre). Lecture seule pour le MVP :
la table `tarif_encre` (type, prix/kg, ratio g/m²/couleur) existe déjà mais
n'avait aucune API exposée. L'édition complète viendra avec la Phase 2
(réconciliation config↔moteur). Scopé `user.entreprise_id`.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import TarifEncre, User
from app.schemas.tarif_encre import TarifEncreRead
from app.services.scope_service import scope_to_entreprise

router = APIRouter(prefix="/api/tarif-encre", tags=["tarif-encre"])


@router.get("", response_model=list[TarifEncreRead])
def list_tarif_encre(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        scope_to_entreprise(db.query(TarifEncre), TarifEncre, user)
        .order_by(TarifEncre.id)
        .all()
    )
