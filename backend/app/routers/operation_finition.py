"""Router /api/operations-finition — Sprint 12-C scoped."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import operation_finition as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import OperationFinition, User
from app.schemas.operation_finition import (
    OperationFinitionCreate,
    OperationFinitionRead,
    OperationFinitionUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/operations-finition", tags=["operations-finition"])


@router.get("", response_model=list[OperationFinitionRead])
def list_operations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(
        db.query(OperationFinition), OperationFinition, user
    )
    return query.order_by(OperationFinition.id).offset(skip).limit(limit).all()


@router.get("/{op_id}", response_model=OperationFinitionRead)
def get_operation(
    op_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, OperationFinition, op_id, user)


@router.post(
    "", response_model=OperationFinitionRead, status_code=status.HTTP_201_CREATED
)
def create_operation(
    data: OperationFinitionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_operation(db, data, entreprise_id=user.entreprise_id)


@router.put("/{op_id}", response_model=OperationFinitionRead)
def update_operation(
    op_id: int,
    data: OperationFinitionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, OperationFinition, op_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{op_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation(
    op_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, OperationFinition, op_id, user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
