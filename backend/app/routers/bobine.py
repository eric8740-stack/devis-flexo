"""Router /api/bobines — Module Stock S1 (granularité A : 1 ligne = 1 bobine).

CRUD complet du stock physique de bobines, multi-tenant strict via
`get_or_404_scoped` + `scope_to_entreprise`. Module ADDITIF : aucun endpoint
existant modifié, aucune lecture par le cost_engine / bat_calculs / optimiser_pose
/ devis. Mouvements (S2) et lien devis↔stock (S3) viendront plus tard.

À la création : `matiere_id` est vérifié scopé tenant (404 anti-énumération si
hors périmètre) et `epaisseur_microns` est pré-rempli depuis la matière si non
fourni. `ml_restant` initial = `ml_initial`.
"""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Bobine, Matiere, User
from app.schemas.bobine import BobineCreate, BobineOut, BobineUpdate
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/bobines", tags=["bobines"])


@router.get("", response_model=list[BobineOut])
def list_bobines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    statut: str | None = Query(None, description="Filtre optionnel sur le statut."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Bobine]:
    """Liste paginée des bobines de l'entreprise (tri par emplacement)."""
    query = scope_to_entreprise(db.query(Bobine), Bobine, user)
    if statut is not None:
        query = query.filter(Bobine.statut == statut)
    return (
        query.order_by(Bobine.rangee, Bobine.etage, Bobine.position)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{bobine_id}", response_model=BobineOut)
def get_bobine(
    bobine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bobine:
    return get_or_404_scoped(db, Bobine, bobine_id, user)


@router.post("", response_model=BobineOut, status_code=status.HTTP_201_CREATED)
def create_bobine(
    data: BobineCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bobine:
    """Crée une bobine physique.

    `matiere_id` est vérifié scopé tenant (404 si hors périmètre).
    `epaisseur_microns` est pré-rempli depuis la matière si non fourni.
    `ml_restant` initial = `ml_initial`.
    """
    matiere = get_or_404_scoped(db, Matiere, data.matiere_id, user)
    epaisseur = (
        data.epaisseur_microns
        if data.epaisseur_microns is not None
        else matiere.epaisseur_microns
    )
    bobine = Bobine(
        entreprise_id=user.entreprise_id,
        matiere_id=matiere.id,
        laize_mm=data.laize_mm,
        epaisseur_microns=epaisseur,
        ml_initial=data.ml_initial,
        ml_restant=data.ml_initial,
        rangee=data.rangee,
        etage=data.etage,
        position=data.position,
        statut=data.statut,
    )
    db.add(bobine)
    db.commit()
    db.refresh(bobine)
    return bobine


@router.patch("/{bobine_id}", response_model=BobineOut)
def update_bobine(
    bobine_id: int,
    data: BobineUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bobine:
    """Modifie une bobine (champs partiels). `matiere_id`/`ml_initial` figés."""
    bobine = get_or_404_scoped(db, Bobine, bobine_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(bobine, field, value)
    db.commit()
    db.refresh(bobine)
    return bobine


@router.delete("/{bobine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bobine(
    bobine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Supprime une bobine (scopé tenant). Suppression dure : en S1 la bobine
    n'a pas d'enfants (les mouvements arrivent en S2)."""
    bobine = get_or_404_scoped(db, Bobine, bobine_id, user)
    db.delete(bobine)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
