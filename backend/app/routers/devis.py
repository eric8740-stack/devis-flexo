"""Router HTTP /api/devis (Sprint 4 Lot 4b, S12-C scoped).

6 endpoints CRUD + 1 duplicate + 1 PDF. Chaque endpoint scope par
`user.entreprise_id` via `Depends(get_current_user)`.
"""
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import devis as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Devis, User
from app.schemas.devis_persist import (
    DevisCreate,
    DevisDetail,
    DevisListResponse,
    DevisUpdate,
)
from app.services.pdf_service import generate_devis_pdf
from app.services.scope_service import get_or_404_scoped

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
    user: User = Depends(get_current_user),
):
    items, total = crud.list_devis(
        db,
        entreprise_id=user.entreprise_id,
        page=page,
        per_page=per_page,
        search=search,
        statut=statut,
        sort=sort,
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
def get_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    return crud.get_devis(db, devis_id)


@router.post("", response_model=DevisDetail, status_code=status.HTTP_201_CREATED)
def create_devis(
    payload: DevisCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return crud.create_devis(db, payload, entreprise_id=user.entreprise_id)
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
    devis_id: int,
    payload: DevisUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    try:
        return crud.update_devis(db, devis_id, payload)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc) if isinstance(exc, ValueError) else f"Champ payload manquant : {exc.args[0]}",
        ) from exc


@router.delete("/{devis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    crud.delete_devis(db, devis_id)


@router.post(
    "/{devis_id}/duplicate",
    response_model=DevisDetail,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    return crud.duplicate_devis(db, devis_id)


@router.get("/{devis_id}/pdf")
def download_devis_pdf(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Génère le PDF du devis et le retourne en téléchargement.

    Lot 4f : nom de fichier = {numero}.pdf (Content-Disposition attachment).
    Le service PDF (Lot 4e) lit weasyprint en lazy import — sur Linux
    Docker prod, les libs natives sont installées via Dockerfile.
    """
    get_or_404_scoped(db, Devis, devis_id, user)
    devis = crud.get_devis(db, devis_id)
    pdf_bytes = generate_devis_pdf(devis, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{devis.numero}.pdf"'
        },
    )
