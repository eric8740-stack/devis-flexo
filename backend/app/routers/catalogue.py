from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import catalogue as crud
from app.db import get_db
from app.schemas.catalogue import CatalogueCreate, CatalogueRead, CatalogueUpdate

router = APIRouter(prefix="/api/catalogue", tags=["catalogue"])


@router.get("", response_model=list[CatalogueRead])
def list_catalogue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    client_id: int | None = Query(
        default=None,
        description="Filtre : ne renvoie que les produits du client donné",
    ),
    db: Session = Depends(get_db),
):
    return crud.list_catalogue(db, skip=skip, limit=limit, client_id=client_id)


@router.get("/{item_id}", response_model=CatalogueRead)
def get_catalogue(item_id: int, db: Session = Depends(get_db)):
    item = crud.get_catalogue(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalogue {item_id} introuvable",
        )
    return item


@router.post(
    "", response_model=CatalogueRead, status_code=status.HTTP_201_CREATED
)
def create_catalogue(data: CatalogueCreate, db: Session = Depends(get_db)):
    return crud.create_catalogue(db, data)


@router.put("/{item_id}", response_model=CatalogueRead)
def update_catalogue(
    item_id: int, data: CatalogueUpdate, db: Session = Depends(get_db)
):
    item = crud.update_catalogue(db, item_id, data)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalogue {item_id} introuvable",
        )
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalogue(item_id: int, db: Session = Depends(get_db)):
    if not crud.delete_catalogue(db, item_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalogue {item_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
