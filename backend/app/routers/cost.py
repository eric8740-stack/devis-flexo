"""Endpoint HTTP du moteur de coût v2 (S3 Lot 3f + S7 Lot 7e).

Un seul endpoint actif : POST /api/cost/calculer

Sprint 7 Lot 7e : retour conditionné par devis.mode_calcul :
  - 'manuel'   → DevisOutput (1 résultat, format Sprint 5)
  - 'matching' → DevisOutputMatching (1-3 candidats cylindres)

Discriminant côté Pydantic v2 = champ `mode` Literal["manuel"] / Literal["matching"]
sur les deux schémas. FastAPI génère un OpenAPI propre via Union discriminée.

Les 7 calculateurs et l'orchestrateur sont dans `app/services/cost_engine/`.
Les erreurs métier (CostEngineError) sont converties en HTTP 422 par un
handler global dans `app/main.py` — pas de try/except local ici.
"""
from typing import Annotated, Union

from fastapi import APIRouter, Depends, status
from pydantic import Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.devis import DevisInput, DevisOutput, DevisOutputMatching
from app.services.cost_engine import MoteurDevis

router = APIRouter(prefix="/api/cost", tags=["cost"])

# Union discriminée par le champ `mode` (Literal sur chaque schéma).
# FastAPI sérialise correctement et OpenAPI distingue les 2 réponses.
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
    payload: DevisInput, db: Session = Depends(get_db)
) -> DevisOutput | DevisOutputMatching:
    return MoteurDevis(db).calculer(payload)
