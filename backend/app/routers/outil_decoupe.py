"""Endpoints HTTP du catalogue des outils de découpe.

Sprint 5 Lot 5b : lecture seule via GET /api/outils (select frontend).
Sprint 9 v2 Lot 9d : CRUD complet (POST/PUT/DELETE/reactiver) + filtre
`include_inactives` sur la liste pour l'UI /parametres/outils.

Pattern de soft delete uniformisé sur les 4 catalogues (machine, complexe,
outil_decoupe, partenaire_st) : DELETE = passage `actif=False`,
POST `/{id}/reactiver` = retour `actif=True`.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import outil_decoupe as crud
from app.db import get_db
from app.schemas.outil_decoupe import (
    OutilDecoupeCreate,
    OutilDecoupeRead,
    OutilDecoupeUpdate,
)

router = APIRouter(prefix="/api/outils", tags=["outils"])


@router.get("", response_model=list[OutilDecoupeRead])
def list_outils(
    include_inactives: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Renvoie les outils de découpe (actifs par défaut, tri par libellé).

    `include_inactives=true` retourne aussi les outils soft-deleted pour
    l'UI /parametres/outils (toggle "Afficher inactifs").
    """
    return crud.list_outils_decoupe(db, include_inactives=include_inactives)


@router.get("/{outil_id}", response_model=OutilDecoupeRead)
def get_outil(outil_id: int, db: Session = Depends(get_db)):
    outil = crud.get_outil_decoupe(db, outil_id)
    if outil is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OutilDecoupe {outil_id} introuvable",
        )
    return outil


@router.post(
    "", response_model=OutilDecoupeRead, status_code=status.HTTP_201_CREATED
)
def create_outil(data: OutilDecoupeCreate, db: Session = Depends(get_db)):
    return crud.create_outil_decoupe(db, data)


@router.put("/{outil_id}", response_model=OutilDecoupeRead)
def update_outil(
    outil_id: int, data: OutilDecoupeUpdate, db: Session = Depends(get_db)
):
    outil = crud.update_outil_decoupe(db, outil_id, data)
    if outil is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OutilDecoupe {outil_id} introuvable",
        )
    return outil


@router.delete("/{outil_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_outil(outil_id: int, db: Session = Depends(get_db)):
    """Soft delete : passe `actif=False` au lieu de supprimer la ligne.

    Préserve l'intégrité historique des devis sauvegardés qui référencent
    `outil_decoupe_id` (snapshot) — l'outil reste consultable individuellement.
    """
    if not crud.soft_delete_outil_decoupe(db, outil_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OutilDecoupe {outil_id} introuvable",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{outil_id}/reactiver", response_model=OutilDecoupeRead)
def reactiver_outil(outil_id: int, db: Session = Depends(get_db)):
    """Réactive un outil soft-deleted (passe `actif=True`)."""
    if not crud.reactiver_outil_decoupe(db, outil_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OutilDecoupe {outil_id} introuvable",
        )
    return crud.get_outil_decoupe(db, outil_id)
