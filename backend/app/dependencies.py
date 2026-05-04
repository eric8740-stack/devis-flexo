"""Dependencies FastAPI — Sprint 12 multi-tenant.

`get_current_user(token, db) -> User` :
  - Décode JWT Bearer (type=access)
  - Lookup User en BDD
  - 401 si token invalide/expiré ou user absent
  - 403 si is_active=False (email non confirmé)

`get_current_admin(user) -> User` :
  - Wrap get_current_user
  - 403 si is_admin=False

À importer depuis les routers Sprint 12-C pour scoper les requêtes par
`current_user.entreprise_id` (cf. brief §5.4).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.auth_service import AuthError, decode_token

# `auto_error=False` : on gère le 401 nous-mêmes pour message custom.
# `tokenUrl` : utilisé par Swagger UI pour le bouton "Authorize" — pointe
# sur notre endpoint /login (renvoie un access_token Bearer).
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login", auto_error=False
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Décode JWT access + récupère User en BDD. Lève 401/403 si invalide."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token, expected_type="access")
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload invalid (sub missing or non-integer)",
        ) from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Confirm your email first.",
        )
    return user


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Wrap get_current_user + 403 si is_admin=False."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user
