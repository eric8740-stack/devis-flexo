"""Router /api/admin — Sprint 12 Lot S12-D.

5 endpoints réservés à Eric (compte admin avec `is_admin=True`) pour
gérer les comptes utilisateurs depuis l'interface admin :

- GET    /api/admin/users               liste tous les users
- POST   /api/admin/users               création manuelle d'un compte
- PUT    /api/admin/users/{id}/disable  désactiver (is_active=False)
- PUT    /api/admin/users/{id}/enable   réactiver (is_active=True)
- DELETE /api/admin/users/{id}          suppression définitive (CASCADE)

Tous protégés par `Depends(get_current_admin)` — un user normal reçoit
403. Garde-fous : impossible pour Eric de se supprimer lui-même ou de
supprimer le compte demo (sécurité produit).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_admin
from app.models import Entreprise, User
from app.schemas.admin import AdminUserCreate, AdminUserRead
from app.services.auth_service import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Helpers d'enrichissement (joindre nom_entreprise + is_demo)
# ---------------------------------------------------------------------------


def _attach_entreprise_fields(user: User, db: Session) -> User:
    """Pose les attributs dynamiques `nom_entreprise` + `is_demo` sur le user
    avant la sérialisation Pydantic via `from_attributes`.
    """
    entreprise = db.get(Entreprise, user.entreprise_id)
    setattr(
        user,
        "nom_entreprise",
        entreprise.raison_sociale if entreprise else "",
    )
    setattr(user, "is_demo", bool(entreprise.is_demo) if entreprise else False)
    return user


# ---------------------------------------------------------------------------
# GET /api/admin/users — liste tous les users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[AdminUserRead])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[User]:
    """Retourne tous les users (avec nom_entreprise joint), tri id ASC."""
    users = db.query(User).order_by(User.id).all()
    return [_attach_entreprise_fields(u, db) for u in users]


# ---------------------------------------------------------------------------
# POST /api/admin/users — création manuelle (atomique entreprise + user)
# ---------------------------------------------------------------------------


@router.post(
    "/users",
    response_model=AdminUserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> User:
    """Création manuelle par admin : pas d'email confirmation, is_active=True.

    Atomique : Entreprise + User dans la même transaction. Si l'email est
    déjà pris → 409 (UNIQUE constraint sur user.email).
    """
    # Pré-check email pour message propre (le 409 IntegrityError est aussi
    # capté par le handler global, mais on préfère être explicite ici).
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {payload.email} déjà utilisé",
        )

    entreprise = Entreprise(
        raison_sociale=payload.nom_entreprise,
        siret="00000000000000",
        is_demo=False,
    )
    db.add(entreprise)
    db.flush()  # nécessaire pour récupérer entreprise.id avant l'insert User

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        nom_contact=payload.nom_contact,
        entreprise_id=entreprise.id,
        is_active=True,
        is_admin=payload.is_admin,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Violation de contrainte (email déjà existant ?)",
        ) from exc
    db.refresh(user)
    return _attach_entreprise_fields(user, db)


# ---------------------------------------------------------------------------
# PUT /api/admin/users/{id}/disable et /enable — toggle is_active
# ---------------------------------------------------------------------------


@router.put("/users/{user_id}/disable", response_model=AdminUserRead)
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> User:
    """Désactive un compte. Le user ne peut plus se connecter (403 sur /me)."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de désactiver son propre compte",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} introuvable",
        )
    user.is_active = False
    db.commit()
    db.refresh(user)
    return _attach_entreprise_fields(user, db)


@router.put("/users/{user_id}/enable", response_model=AdminUserRead)
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> User:
    """Réactive un compte (is_active=True)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} introuvable",
        )
    user.is_active = True
    db.commit()
    db.refresh(user)
    return _attach_entreprise_fields(user, db)


# ---------------------------------------------------------------------------
# DELETE /api/admin/users/{id} — suppression définitive (CASCADE entreprise)
# ---------------------------------------------------------------------------


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> None:
    """Suppression définitive : supprime l'Entreprise (CASCADE → toutes les
    données scopées : machines, devis, tarifs, ...) puis le User.

    Garde-fous :
    - refus du suicide (admin tentant de se supprimer)
    - refus de supprimer un compte `is_demo=True` (le compte demo est
      sacré pour la défendabilité — sacrés EXACT préservés)
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de supprimer son propre compte",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} introuvable",
        )
    entreprise = db.get(Entreprise, user.entreprise_id)
    if entreprise is not None and entreprise.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de supprimer le compte demo (réservé Eric)",
        )

    # CASCADE : supprimer l'Entreprise déclenche le ON DELETE CASCADE sur
    # toutes les FK pointant vers entreprise.id (machines, devis, tarifs...)
    # ainsi que sur user.entreprise_id (qui supprime le User en chaîne).
    if entreprise is not None:
        db.delete(entreprise)
    else:
        # Cas dégénéré : user orphelin sans entreprise — supprimer juste le user
        db.delete(user)
    db.commit()
