"""Router /api/cylindres — Brief #29 paramètres parc.

CRUD complet du parc de cylindres magnétiques d'une imprimerie.
Multi-tenant strict via `get_or_404_scoped` + `scope_to_entreprise`.
Soft delete uniformisé (`actif=False`) — pas de suppression dure
pour préserver les FK historiques (devis, lots_production).

Convention métier : l'API accepte/expose `nb_dents` (nomenclature
flexo) ; conversion vers `developpe_mm = nb_dents × 3.175` côté CRUD.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import CylindreMagnetique, User
from app.schemas.cylindre import CylindreCreate, CylindreRead, CylindreUpdate
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/cylindres", tags=["cylindres"])

# Pas de dent ≠ pas, gardé en synchro avec catalogue_defaults.DENTS_TO_MM_FACTOR.
DENTS_TO_MM = Decimal("3.175")


def _to_read(cyl: CylindreMagnetique) -> CylindreRead:
    """Compose la sortie API depuis le row DB.

    Le modèle stocke `developpe_mm` ; on calcule `nb_dents` par round
    pour l'affichage métier (cohérent avec la conversion à l'insert).
    """
    nb_dents = int(round(float(cyl.developpe_mm) / float(DENTS_TO_MM)))
    return CylindreRead(
        id=cyl.id,
        nb_dents=nb_dents,
        developpe_mm=cyl.developpe_mm,
        actif=cyl.actif,
        notes=cyl.notes,
        date_creation=cyl.date_creation,
    )


@router.get("", response_model=list[CylindreRead])
def list_cylindres(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    actif: bool | None = Query(
        True, description="Filtre actif=True par défaut. None = tous."
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CylindreRead]:
    """Liste paginée des cylindres de l'entreprise.

    Filtre `actif=True` par défaut (suppression douce). Passer `?actif=`
    sans valeur pour récupérer aussi les cyls désactivés (admin parc).
    """
    query = scope_to_entreprise(db.query(CylindreMagnetique), CylindreMagnetique, user)
    if actif is True:
        query = query.filter(CylindreMagnetique.actif.is_(True))
    elif actif is False:
        query = query.filter(CylindreMagnetique.actif.is_(False))
    rows = (
        query.order_by(CylindreMagnetique.developpe_mm)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_read(c) for c in rows]


@router.get("/{cylindre_id}", response_model=CylindreRead)
def get_cylindre(
    cylindre_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CylindreRead:
    cyl = get_or_404_scoped(db, CylindreMagnetique, cylindre_id, user)
    return _to_read(cyl)


@router.post("", response_model=CylindreRead, status_code=status.HTTP_201_CREATED)
def create_cylindre(
    data: CylindreCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CylindreRead:
    """Crée un cylindre. La nomenclature `nb_dents` est convertie en
    `developpe_mm` à l'insert pour rester cohérent avec le moteur."""
    developpe_mm = (Decimal(data.nb_dents) * DENTS_TO_MM).quantize(Decimal("0.01"))
    cyl = CylindreMagnetique(
        entreprise_id=user.entreprise_id,
        developpe_mm=developpe_mm,
        actif=data.actif,
        notes=data.notes,
    )
    db.add(cyl)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cylindre incompatible (contrainte BDD).",
        ) from exc
    db.refresh(cyl)
    return _to_read(cyl)


@router.patch("/{cylindre_id}", response_model=CylindreRead)
def update_cylindre(
    cylindre_id: int,
    data: CylindreUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CylindreRead:
    """Modifie un cylindre (champs partiels). Si `nb_dents` change,
    `developpe_mm` est recalculé."""
    cyl = get_or_404_scoped(db, CylindreMagnetique, cylindre_id, user)
    fields = data.model_dump(exclude_unset=True)
    if "nb_dents" in fields:
        cyl.developpe_mm = (
            Decimal(fields.pop("nb_dents")) * DENTS_TO_MM
        ).quantize(Decimal("0.01"))
    for field, value in fields.items():
        setattr(cyl, field, value)
    db.commit()
    db.refresh(cyl)
    return _to_read(cyl)


@router.delete("/{cylindre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cylindre(
    cylindre_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Soft delete : `actif=False`. Préserve les FK historiques (devis
    sauvegardés sur ce cyl, lots_production)."""
    cyl = get_or_404_scoped(db, CylindreMagnetique, cylindre_id, user)
    cyl.actif = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{cylindre_id}/toggle-actif", response_model=CylindreRead)
def toggle_actif_cylindre(
    cylindre_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CylindreRead:
    """Bascule actif/inactif (alternative au DELETE pour réactiver)."""
    cyl = get_or_404_scoped(db, CylindreMagnetique, cylindre_id, user)
    cyl.actif = not cyl.actif
    db.commit()
    db.refresh(cyl)
    return _to_read(cyl)
