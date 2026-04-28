"""Endpoint HTTP du moteur de coût v2 (S3 Lot 3f).

Un seul endpoint actif : POST /api/cost/calculer (DevisInput -> DevisOutput).

Les 7 calculateurs et l'orchestrateur sont dans `app/services/cost_engine/`.
Les erreurs métier (CostEngineError) sont converties en HTTP 422 par un
handler global dans `app/main.py` — pas de try/except local ici, on laisse
remonter pour préserver le pattern.

Périmètre 3f : un seul POST. Les routers de listage des tarifs/encres/etc.
viendront en 3g si besoin frontend.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.devis import DevisInput, DevisOutput
from app.services.cost_engine import MoteurDevis

router = APIRouter(prefix="/api/cost", tags=["cost"])


@router.post(
    "/calculer",
    response_model=DevisOutput,
    status_code=status.HTTP_200_OK,
    summary="Calcule un devis selon le moteur de coût v2 (7 postes)",
)
def calculer_devis(payload: DevisInput, db: Session = Depends(get_db)) -> DevisOutput:
    return MoteurDevis(db).calculer(payload)
