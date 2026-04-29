"""Router HTTP /api/devis (Sprint 4 Lot 4b).

6 endpoints : GET list, GET detail, POST create, PUT update, DELETE,
POST duplicate. Le PDF arrive en Lot 4f (endpoint séparé).
"""
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import devis as crud
from app.db import get_db
from app.schemas.devis_persist import (
    DevisCreate,
    DevisDetail,
    DevisListResponse,
    DevisUpdate,
)

router = APIRouter(prefix="/api/devis", tags=["devis"])


@router.get("", response_model=DevisListResponse)
def list_devis(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche numéro ou nom client"),
    statut: Literal["brouillon", "valide"] | None = Query(None),
    sort: Literal["date_desc", "date_asc", "numero_asc", "ht_desc"] = Query(
        "date_desc"
    ),
    db: Session = Depends(get_db),
):
    items, total = crud.list_devis(
        db, page=page, per_page=per_page, search=search, statut=statut, sort=sort
    )
    pages = max(1, math.ceil(total / per_page)) if total else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get("/{devis_id}", response_model=DevisDetail)
def get_devis(devis_id: int, db: Session = Depends(get_db)):
    devis = crud.get_devis(db, devis_id)
    if devis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devis {devis_id} introuvable",
        )
    return devis


@router.post("", response_model=DevisDetail, status_code=status.HTTP_201_CREATED)
def create_devis(payload: DevisCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_devis(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Champ payload manquant : {exc.args[0]}",
        ) from exc


@router.put("/{devis_id}", response_model=DevisDetail)
def update_devis(
    devis_id: int, payload: DevisUpdate, db: Session = Depends(get_db)
):
    try:
        devis = crud.update_devis(db, devis_id, payload)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc) if isinstance(exc, ValueError) else f"Champ payload manquant : {exc.args[0]}",
        ) from exc
    if devis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devis {devis_id} introuvable",
        )
    return devis


@router.delete("/{devis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_devis(devis_id: int, db: Session = Depends(get_db)):
    if not crud.delete_devis(db, devis_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devis {devis_id} introuvable",
        )


@router.post(
    "/{devis_id}/duplicate",
    response_model=DevisDetail,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_devis(devis_id: int, db: Session = Depends(get_db)):
    nouveau = crud.duplicate_devis(db, devis_id)
    if nouveau is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devis {devis_id} introuvable",
        )
    return nouveau
