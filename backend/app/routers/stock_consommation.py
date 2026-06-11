"""Router lien devis↔stock — Module Stock S3.

Endpoints sous `/api/devis/{id}/...` (additifs, ne modifient PAS le routeur devis
ni le chiffrage). Multi-tenant strict : `get_or_404_scoped` sur le devis ET sur
chaque bobine. La consommation réutilise `MouvementStock` (type `sortie`,
`devis_id`) ; « déjà consommé » se déduit des mouvements (pas de flag sur Devis).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Bobine, Devis, MouvementStock, User
from app.schemas.stock_consommation import (
    ConsommationResult,
    ConsommerIn,
    PropositionOut,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise
from app.services.stock_consommation import etat_consommation, proposition_fifo

router = APIRouter(prefix="/api/devis", tags=["stock-consommation"])


@router.get("/{devis_id}/proposition-consommation", response_model=PropositionOut)
def proposition_consommation(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Proposition FIFO des bobines couvrant le besoin matière du devis.

    `ml_requis` = `bobinage.ml_total` (calcul F, lecture). `stock_suffisant` /
    `manque_ml` indiquent une éventuelle insuffisance — NON bloquante.
    """
    devis = get_or_404_scoped(db, Devis, devis_id, user)
    return proposition_fifo(db, devis, user)


@router.post(
    "/{devis_id}/consommer",
    response_model=ConsommationResult,
    status_code=status.HTTP_201_CREATED,
)
def consommer(
    devis_id: int,
    data: ConsommerIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConsommationResult:
    """Consomme le stock pour ce devis : 1 mouvement `sortie` par ligne.

    ATOMIQUE (tout ou rien) : toutes les bobines sont validées AVANT toute
    écriture ; si une ligne dépasse `ml_restant` → 409, aucun effet.
    """
    devis = get_or_404_scoped(db, Devis, devis_id, user)
    # Garde back contre la double consommation (indépendante du front).
    deja_consomme, _, _ = etat_consommation(db, devis, user)
    if deja_consomme:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Devis déjà consommé — annuler la consommation avant de reconsommer.",
        )
    # Validation préalable complète (atomicité : on n'écrit qu'après).
    plan: list[tuple[Bobine, int]] = []
    for ligne in data.lignes:
        bobine = get_or_404_scoped(db, Bobine, ligne.bobine_id, user)
        if ligne.ml > bobine.ml_restant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Stock insuffisant sur bobine {bobine.id} : "
                    f"{ligne.ml} ml demandés, {bobine.ml_restant} ml restants."
                ),
            )
        plan.append((bobine, ligne.ml))

    mouvements: list[MouvementStock] = []
    for bobine, ml in plan:
        ml_avant = bobine.ml_restant
        bobine.ml_restant = ml_avant - ml
        mv = MouvementStock(
            entreprise_id=user.entreprise_id,
            bobine_id=bobine.id,
            devis_id=devis.id,
            type="sortie",
            ml=ml,
            ml_avant=ml_avant,
            ml_apres=bobine.ml_restant,
            motif=f"Consommation devis {devis.numero}",
        )
        db.add(mv)
        mouvements.append(mv)
    db.commit()
    bobines = [b for b, _ in plan]
    for mv in mouvements:
        db.refresh(mv)
    for b in bobines:
        db.refresh(b)
    return ConsommationResult(mouvements=mouvements, bobines=bobines)


@router.post(
    "/{devis_id}/annuler-consommation",
    response_model=ConsommationResult,
    status_code=status.HTTP_201_CREATED,
)
def annuler_consommation(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConsommationResult:
    """Annule la consommation : mouvement `entree` inverse par bobine.

    Idempotent : on ré-entre le NET encore consommé par ce devis
    (`Σ sortie − Σ entree`) par bobine ; un 2ᵉ appel ne fait rien.
    """
    devis = get_or_404_scoped(db, Devis, devis_id, user)
    mvts = (
        scope_to_entreprise(db.query(MouvementStock), MouvementStock, user)
        .filter(MouvementStock.devis_id == devis.id)
        .all()
    )
    # Net consommé par bobine = sorties − entrées (déjà annulées).
    net: dict[int, int] = {}
    for mv in mvts:
        signe = 1 if mv.type == "sortie" else -1
        net[mv.bobine_id] = net.get(mv.bobine_id, 0) + signe * mv.ml

    mouvements: list[MouvementStock] = []
    bobines: list[Bobine] = []
    for bobine_id, reste in net.items():
        if reste <= 0:
            continue
        bobine = get_or_404_scoped(db, Bobine, bobine_id, user)
        ml_avant = bobine.ml_restant
        bobine.ml_restant = ml_avant + reste
        mv = MouvementStock(
            entreprise_id=user.entreprise_id,
            bobine_id=bobine.id,
            devis_id=devis.id,
            type="entree",
            ml=reste,
            ml_avant=ml_avant,
            ml_apres=bobine.ml_restant,
            motif=f"Annulation consommation devis {devis.numero}",
        )
        db.add(mv)
        mouvements.append(mv)
        bobines.append(bobine)
    db.commit()
    for mv in mouvements:
        db.refresh(mv)
    for b in bobines:
        db.refresh(b)
    return ConsommationResult(mouvements=mouvements, bobines=bobines)
