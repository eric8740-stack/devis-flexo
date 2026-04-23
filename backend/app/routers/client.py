from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import client as crud
from app.db import get_db
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_clients(db, skip=skip, limit=limit)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = crud.get_client(db, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} introuvable",
        )
    return client


@router.post(
    "", response_model=ClientRead, status_code=status.HTTP_201_CREATED
)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    return crud.create_client(db, data)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: int, data: ClientUpdate, db: Session = Depends(get_db)
):
    client = crud.update_client(db, client_id, data)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} introuvable",
        )
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    if not crud.delete_client(db, client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
