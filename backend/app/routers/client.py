"""Router /api/clients — Sprint 12-C scoped."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import client as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Client, User
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = scope_to_entreprise(db.query(Client), Client, user)
    return query.order_by(Client.id).offset(skip).limit(limit).all()


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_or_404_scoped(db, Client, client_id, user)


@router.post(
    "", response_model=ClientRead, status_code=status.HTTP_201_CREATED
)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud.create_client(db, data, entreprise_id=user.entreprise_id)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Client, client_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_or_404_scoped(db, Client, client_id, user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
