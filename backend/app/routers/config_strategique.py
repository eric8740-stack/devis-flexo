"""Router /api/strategique — onglet Stratégique (Brief stratégique v2, Phase 1).

Config par entreprise, scopée `user.entreprise_id` :
  - /couts        GET (get-or-create) · PUT (upsert partiel)   — singleton
  - /changements  GET (get-or-create) · PUT (upsert partiel)   — singleton
  - /roulage      GET (liste) · POST · PUT/{id} · DELETE/{id}   — collection
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.crud import config_strategique as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import ConfigRoulage, User
from app.schemas.config_strategique import (
    ConfigChangementsRead,
    ConfigChangementsUpdate,
    ConfigCoutsRead,
    ConfigCoutsUpdate,
    ConfigRoulageCreate,
    ConfigRoulageRead,
    ConfigRoulageUpdate,
)
from app.services.scope_service import get_or_404_scoped

router = APIRouter(prefix="/api/strategique", tags=["strategique"])


# --- Coûts & marges (singleton) -------------------------------------------
@router.get("/couts", response_model=ConfigCoutsRead)
def get_couts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.get_or_create_couts(db, user.entreprise_id)


@router.put("/couts", response_model=ConfigCoutsRead)
def update_couts(
    data: ConfigCoutsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.update_couts(db, user.entreprise_id, data)


# --- Changements (singleton) ----------------------------------------------
@router.get("/changements", response_model=ConfigChangementsRead)
def get_changements(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.get_or_create_changements(db, user.entreprise_id)


@router.put("/changements", response_model=ConfigChangementsRead)
def update_changements(
    data: ConfigChangementsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.update_changements(db, user.entreprise_id, data)


# --- Roulage (collection par format) --------------------------------------
@router.get("/roulage", response_model=list[ConfigRoulageRead])
def list_roulage(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.list_roulage(db, user.entreprise_id)


@router.post(
    "/roulage",
    response_model=ConfigRoulageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_roulage(
    data: ConfigRoulageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_roulage(db, data, entreprise_id=user.entreprise_id)


@router.put("/roulage/{roulage_id}", response_model=ConfigRoulageRead)
def update_roulage(
    roulage_id: int,
    data: ConfigRoulageUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, ConfigRoulage, roulage_id, user)
    return crud.update_roulage(db, item, data)


@router.delete("/roulage/{roulage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roulage(
    roulage_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, ConfigRoulage, roulage_id, user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
