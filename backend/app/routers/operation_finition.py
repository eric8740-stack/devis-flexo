from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import operation_finition as crud
from app.db import get_db
from app.schemas.operation_finition import (
    OperationFinitionCreate,
    OperationFinitionRead,
    OperationFinitionUpdate,
)

router = APIRouter(prefix="/api/operations-finition", tags=["operations-finition"])


@router.get("", response_model=list[OperationFinitionRead])
def list_operations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_operations(db, skip=skip, limit=limit)


@router.get("/{op_id}", response_model=OperationFinitionRead)
def get_operation(op_id: int, db: Session = Depends(get_db)):
    op = crud.get_operation(db, op_id)
    if op is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OperationFinition {op_id} introuvable",
        )
    return op


@router.post(
    "", response_model=OperationFinitionRead, status_code=status.HTTP_201_CREATED
)
def create_operation(
    data: OperationFinitionCreate, db: Session = Depends(get_db)
):
    return crud.create_operation(db, data)


@router.put("/{op_id}", response_model=OperationFinitionRead)
def update_operation(
    op_id: int, data: OperationFinitionUpdate, db: Session = Depends(get_db)
):
    op = crud.update_operation(db, op_id, data)
    if op is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OperationFinition {op_id} introuvable",
        )
    return op


@router.delete("/{op_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation(op_id: int, db: Session = Depends(get_db)):
    if not crud.delete_operation(db, op_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OperationFinition {op_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
