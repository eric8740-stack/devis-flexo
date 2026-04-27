from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import machine as crud
from app.db import get_db
from app.schemas.machine import MachineCreate, MachineRead, MachineUpdate

router = APIRouter(prefix="/api/machines", tags=["machines"])


@router.get("", response_model=list[MachineRead])
def list_machines(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_machines(db, skip=skip, limit=limit)


@router.get("/{machine_id}", response_model=MachineRead)
def get_machine(machine_id: int, db: Session = Depends(get_db)):
    m = crud.get_machine(db, machine_id)
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine {machine_id} introuvable",
        )
    return m


@router.post("", response_model=MachineRead, status_code=status.HTTP_201_CREATED)
def create_machine(data: MachineCreate, db: Session = Depends(get_db)):
    return crud.create_machine(db, data)


@router.put("/{machine_id}", response_model=MachineRead)
def update_machine(
    machine_id: int, data: MachineUpdate, db: Session = Depends(get_db)
):
    m = crud.update_machine(db, machine_id, data)
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine {machine_id} introuvable",
        )
    return m


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    if not crud.delete_machine(db, machine_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine {machine_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
