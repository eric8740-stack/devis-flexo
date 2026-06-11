"""Router mouvements de stock — Module Stock S2.

Endpoints TRANSACTIONNELS : un POST mouvement ajuste `Bobine.ml_restant` ET crée
la ligne de journal dans un seul commit (atomique). Multi-tenant strict via
`get_or_404_scoped` (bobine scopée → 404 anti-énumération) + `scope_to_entreprise`.

Module ADDITIF : aucun endpoint existant modifié ; le PATCH `ml_restant` direct
de S1 reste fonctionnel mais est DÉPRÉCIÉ au profit d'un mouvement `inventaire`
(qui trace l'audit ancien→nouveau).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Bobine, MouvementStock, User
from app.schemas.mouvement_stock import (
    MouvementCreate,
    MouvementOut,
    MouvementResult,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api", tags=["mouvements-stock"])


@router.post(
    "/bobines/{bobine_id}/mouvements",
    response_model=MouvementResult,
    status_code=status.HTTP_201_CREATED,
)
def creer_mouvement(
    bobine_id: int,
    data: MouvementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MouvementResult:
    """Crée un mouvement et ajuste `ml_restant` (transactionnel, atomique).

    - `entree`     : `ml_restant += ml`
    - `sortie`     : refus 409 si `ml > ml_restant` (jamais négatif), sinon `−ml`
    - `inventaire` : `ml_restant = ml` (correction), audit ancien→nouveau
    """
    bobine = get_or_404_scoped(db, Bobine, bobine_id, user)
    ml_avant = bobine.ml_restant

    if data.type == "entree":
        ml_apres = ml_avant + data.ml
    elif data.type == "sortie":
        if data.ml > ml_avant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Stock insuffisant : {data.ml} ml demandés, "
                    f"{ml_avant} ml restants."
                ),
            )
        ml_apres = ml_avant - data.ml
    else:  # inventaire — `ml` est la nouvelle valeur cible
        ml_apres = data.ml

    mouvement = MouvementStock(
        entreprise_id=user.entreprise_id,
        bobine_id=bobine.id,
        type=data.type,
        ml=data.ml,
        ml_avant=ml_avant,
        ml_apres=ml_apres,
        motif=data.motif,
        reference=data.reference,
    )
    bobine.ml_restant = ml_apres
    db.add(mouvement)
    db.commit()  # un seul commit : mouvement + bobine appliqués atomiquement
    db.refresh(mouvement)
    db.refresh(bobine)
    return MouvementResult(mouvement=mouvement, bobine=bobine)


@router.get(
    "/bobines/{bobine_id}/mouvements", response_model=list[MouvementOut]
)
def historique_bobine(
    bobine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MouvementStock]:
    """Historique des mouvements d'une bobine (plus récent d'abord)."""
    get_or_404_scoped(db, Bobine, bobine_id, user)  # vérifie le scope tenant
    return (
        scope_to_entreprise(db.query(MouvementStock), MouvementStock, user)
        .filter(MouvementStock.bobine_id == bobine_id)
        .order_by(MouvementStock.date_creation.desc(), MouvementStock.id.desc())
        .all()
    )


@router.get("/mouvements", response_model=list[MouvementOut])
def liste_mouvements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    type: str | None = Query(None, description="Filtre optionnel sur le type."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MouvementStock]:
    """Journal des mouvements du tenant (plus récent d'abord), paginé."""
    query = scope_to_entreprise(db.query(MouvementStock), MouvementStock, user)
    if type is not None:
        query = query.filter(MouvementStock.type == type)
    return (
        query.order_by(
            MouvementStock.date_creation.desc(), MouvementStock.id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
