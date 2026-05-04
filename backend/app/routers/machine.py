"""Router /api/machines — Sprint 12-C scoped + soft delete (S9 v2 conservé)."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import machine as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Machine, User
from app.schemas.machine import MachineCreate, MachineRead, MachineUpdate
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/machines", tags=["machines"])


@router.get("", response_model=list[MachineRead])
def list_machines(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_inactives: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(db.query(Machine), Machine, user)
    if not include_inactives:
        query = query.filter(Machine.actif.is_(True))
    return query.order_by(Machine.id).offset(skip).limit(limit).all()


@router.get("/{machine_id}", response_model=MachineRead)
def get_machine(
    machine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, Machine, machine_id, user)


@router.post("", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(
    data: MachineCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_machine(db, data, entreprise_id=user.entreprise_id)


@router.put("/{machine_id}", response_model=MachineRead)
def update_machine(
    machine_id: int,
    data: MachineUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Machine, machine_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(
    machine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sprint 9 v2 — soft delete (`actif=False`). Sprint 12-C — scope user."""
    item = get_or_404_scoped(db, Machine, machine_id, user)
    item.actif = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{machine_id}/reactiver", response_model=MachineRead)
def reactiver_machine(
    machine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Machine, machine_id, user)
    item.actif = True
    db.commit()
    db.refresh(item)
    return item
