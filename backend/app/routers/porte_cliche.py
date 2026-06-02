"""Router /api/porte-cliches refondu — Brief #30.

CRUD complet des porte-clichés (cyls engrenage synchronisés au cyl
magnétique). Multi-tenant strict + soft delete + toggle actif.

Refonte vs PR #29 :
- Schéma porté sur machine_id + cylindre_id + quantite (cf modèle PR #30).
- Validation : machine et cylindre doivent appartenir au même tenant.
- Default applicatif : `quantite = machine.nb_groupes_couleurs` (8 si NULL).
- Filtre query : `?machine_id=X` pour l'UI onglet PC (filtre par machine).
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import (
    CylindreMagnetique,
    Machine,
    PorteCliche,
    User,
)
from app.schemas.porte_cliche import (
    PorteClicheCreate,
    PorteClicheRead,
    PorteClicheUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise

router = APIRouter(prefix="/api/porte-cliches", tags=["porte-cliches"])

# Fallback nb couleurs si la machine n'a pas de valeur saisie.
DEFAULT_NB_COULEURS_FALLBACK = 8
# 1 dent = 3.175 mm (cf catalogue_defaults.DENTS_TO_MM_FACTOR).
DENTS_TO_MM = Decimal("3.175")


def _enrichir_pour_read(pc: PorteCliche, db: Session) -> PorteClicheRead:
    """Compose la sortie API en joignant machine.nom + cylindre.nb_dents."""
    machine = db.get(Machine, pc.machine_id)
    cyl = db.get(CylindreMagnetique, pc.cylindre_id)
    nb_dents = int(round(float(cyl.developpe_mm) / float(DENTS_TO_MM))) if cyl else 0
    return PorteClicheRead(
        id=pc.id,
        machine_id=pc.machine_id,
        machine_nom=machine.nom if machine else f"Machine #{pc.machine_id}",
        machine_nb_couleurs=machine.nb_groupes_couleurs if machine else None,
        cylindre_id=pc.cylindre_id,
        cylindre_nb_dents=nb_dents,
        cylindre_developpe_mm=str(cyl.developpe_mm) if cyl else "0",
        quantite=pc.quantite,
        notes=pc.notes,
        actif=pc.actif,
        created_at=pc.created_at,
        updated_at=pc.updated_at,
    )


def _verifier_fks_tenant(
    db: Session, user: User, machine_id: int, cylindre_id: int
) -> Machine:
    """Vérifie que machine et cylindre appartiennent au tenant courant.

    Retourne la machine résolue pour permettre au caller de lire son
    nb_groupes_couleurs. 404 si scope mismatch (anti-énumération).
    """
    machine = get_or_404_scoped(db, Machine, machine_id, user)
    get_or_404_scoped(db, CylindreMagnetique, cylindre_id, user)
    return machine


@router.get("", response_model=list[PorteClicheRead])
def list_porte_cliches(
    machine_id: int | None = Query(
        None, description="Filtre par machine (UI onglet PC)."
    ),
    actif: bool | None = Query(
        True, description="Filtre actif=True par défaut. None = tous."
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PorteClicheRead]:
    """Liste paginée des PCs du tenant.

    Filtres : `?machine_id=X` (UI onglet par machine), `?actif=true|false`.
    Le tri est par machine_id puis cylindre developpe_mm (lecture
    cohérente avec le tableau de l'UI).
    """
    query = scope_to_entreprise(db.query(PorteCliche), PorteCliche, user)
    if actif is True:
        query = query.filter(PorteCliche.actif.is_(True))
    elif actif is False:
        query = query.filter(PorteCliche.actif.is_(False))
    if machine_id is not None:
        query = query.filter(PorteCliche.machine_id == machine_id)
    rows = (
        query.order_by(PorteCliche.machine_id, PorteCliche.cylindre_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_enrichir_pour_read(pc, db) for pc in rows]


@router.get("/{porte_cliche_id}", response_model=PorteClicheRead)
def get_porte_cliche(
    porte_cliche_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteClicheRead:
    pc = get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)
    return _enrichir_pour_read(pc, db)


@router.post(
    "", response_model=PorteClicheRead, status_code=status.HTTP_201_CREATED
)
def create_porte_cliche(
    data: PorteClicheCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteClicheRead:
    """Crée un PC. Validations métier :
    - machine_id et cylindre_id appartiennent au tenant courant (404 sinon).
    - Si quantite None → default = machine.nb_groupes_couleurs (fallback 8).
    - UniqueConstraint(entreprise_id, machine_id, cylindre_id) → 409 si conflit.
    """
    machine = _verifier_fks_tenant(db, user, data.machine_id, data.cylindre_id)
    quantite = (
        data.quantite
        if data.quantite is not None
        else (machine.nb_groupes_couleurs or DEFAULT_NB_COULEURS_FALLBACK)
    )
    pc = PorteCliche(
        entreprise_id=user.entreprise_id,
        machine_id=data.machine_id,
        cylindre_id=data.cylindre_id,
        quantite=quantite,
        notes=data.notes,
        actif=data.actif,
    )
    db.add(pc)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Un porte-cliché existe déjà pour cette machine "
                f"({data.machine_id}) et ce cylindre ({data.cylindre_id})."
            ),
        ) from exc
    db.refresh(pc)
    return _enrichir_pour_read(pc, db)


@router.patch("/{porte_cliche_id}", response_model=PorteClicheRead)
def update_porte_cliche(
    porte_cliche_id: int,
    data: PorteClicheUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteClicheRead:
    """Modifie un PC (champs partiels : quantite, notes, actif).

    machine_id et cylindre_id NE sont PAS modifiables — ce sont les
    attributs identifiants. Pour changer de couple, créer un nouveau PC
    et désactiver l'ancien.
    """
    pc = get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pc, field, value)
    db.commit()
    db.refresh(pc)
    return _enrichir_pour_read(pc, db)


@router.delete(
    "/{porte_cliche_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_porte_cliche(
    porte_cliche_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Soft delete : `actif=False`."""
    pc = get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)
    pc.actif = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{porte_cliche_id}/toggle-actif", response_model=PorteClicheRead
)
def toggle_actif_porte_cliche(
    porte_cliche_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PorteClicheRead:
    """Bascule actif/inactif (alternative au DELETE pour réactivation)."""
    pc = get_or_404_scoped(db, PorteCliche, porte_cliche_id, user)
    pc.actif = not pc.actif
    db.commit()
    db.refresh(pc)
    return _enrichir_pour_read(pc, db)
