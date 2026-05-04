"""Endpoint HTTP du moteur de coût v2 — Sprint 12-C scoped.

Un seul endpoint actif : POST /api/cost/calculer

Sprint 12-C : `Depends(get_current_user)` ajouté + validation des IDs
externes (machine_id, complexe_id, partenaire_st_id) qui doivent
appartenir à `user.entreprise_id`. Sinon 404 (anti-enumeration).

Le moteur `MoteurDevis(db, entreprise_id)` reçoit `user.entreprise_id`
pour scoper les lectures `tarif_poste` / `tarif_encre`.
"""
from typing import Annotated, Union

from fastapi import APIRouter, Depends, status
from pydantic import Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Complexe, Machine, PartenaireST, User
from app.schemas.devis import DevisInput, DevisOutput, DevisOutputMatching
from app.services.cost_engine import MoteurDevis
from app.services.scope_service import validate_id_belongs_to_user

router = APIRouter(prefix="/api/cost", tags=["cost"])

# Union discriminée par le champ `mode` (Literal sur chaque schéma).
DevisResponse = Annotated[
    Union[DevisOutput, DevisOutputMatching],
    Field(discriminator="mode"),
]


@router.post(
    "/calculer",
    response_model=DevisResponse,
    status_code=status.HTTP_200_OK,
    summary="Calcule un devis (mode manuel = 1 résultat, mode matching = 1-3 cylindres)",
)
def calculer_devis(
    payload: DevisInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DevisOutput | DevisOutputMatching:
    # Sprint 12-C : valide que les IDs du payload appartiennent à user.entreprise_id
    validate_id_belongs_to_user(db, Machine, payload.machine_id, user)
    validate_id_belongs_to_user(db, Complexe, payload.complexe_id, user)
    for forfait in payload.forfaits_st:
        validate_id_belongs_to_user(
            db, PartenaireST, forfait.partenaire_st_id, user
        )

    return MoteurDevis(db, user.entreprise_id).calculer(payload)
