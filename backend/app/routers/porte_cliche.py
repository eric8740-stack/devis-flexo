"""Router /api/porte-cliches — Brief #29 paramètres parc.

CRUD complet des porte-clichés (sleeves) d'une imprimerie. Multi-tenant
strict via `get_or_404_scoped` + `scope_to_entreprise`. Soft delete
uniformisé (`actif=False`).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import PorteCliche, User
from app.schemas.porte_cliche import (
    PorteClicheCreate,
    PorteClicheRead,
    PorteClicheUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/porte-cliches", tags=["porte-cliches"])


@router.get("", response_model=list[PorteClicheRead])
def list_porte_cliches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    actif: bool | None = Query(
        True, description="Filtre actif=True par défaut. None = tous."
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PorteCliche]:
    """Liste paginée des porte-clichés de l'entreprise."""
    query = scope_to_entreprise(db.query(PorteCliche), PorteCliche, user)
    if actif is True:
        query = query.filter(PorteCliche.actif.is_(True))
    elif actif is False:
        query = query.filter(PorteCliche.actif.is_(False))
    return query.order_by(PorteCliche.reference).offset(skip).limit(limit).all()


@router.get("/{porte_cliche_id}", response_model=PorteClicheRead)
def get_porte_cliche(
    porte_cliche_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteCliche:
    return get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)


@router.post(
    "", response_model=PorteClicheRead, status_code=status.HTTP_201_CREATED
)
def create_porte_cliche(
    data: PorteClicheCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteCliche:
    """Crée un porte-cliché. La référence est unique par entreprise."""
    pc = PorteCliche(
        entreprise_id=user.entreprise_id,
        reference=data.reference,
        marque=data.marque,
        modele=data.modele,
        laize_utile_mm=data.laize_utile_mm,
        diametre_interieur_mm=data.diametre_interieur_mm,
        matiere=data.matiere,
        notes=data.notes,
        actif=data.actif,
    )
    db.add(pc)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Référence '{data.reference}' déjà utilisée pour ce tenant.",
        ) from exc
    db.refresh(pc)
    return pc


@router.patch("/{porte_cliche_id}", response_model=PorteClicheRead)
def update_porte_cliche(
    porte_cliche_id: int,
    data: PorteClicheUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteCliche:
    """Modifie un porte-cliché (champs partiels)."""
    pc = get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pc, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Référence en conflit avec un autre porte-cliché.",
        ) from exc
    db.refresh(pc)
    return pc


@router.delete(
    "/{porte_cliche_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_porte_cliche(
    porte_cliche_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Soft delete : `actif=False`. Pas de suppression dure."""
    pc = get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)
    pc.actif = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{porte_cliche_id}/toggle-actif", response_model=PorteClicheRead
)
def toggle_actif_porte_cliche(
    porte_cliche_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteCliche:
    """Bascule actif/inactif."""
    pc = get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)
    pc.actif = not pc.actif
    db.commit()
    db.refresh(pc)
    return pc
