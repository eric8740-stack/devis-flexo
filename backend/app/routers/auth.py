"""Router /api/auth — Sprint 12 multi-tenant.

8 endpoints couvrant inscription, login, logout, confirmation email,
reset password, refresh token, /me.

Décisions Sprint 12 :
- JWT stateless (pas de table session côté serveur)
- Tokens email confirmation/reset stockés dans User.email_confirmation_token
  et User.password_reset_token avec expiration séparée
- /forgot-password retourne toujours 200 (anti-enumeration : pas de
  divulgation "cet email n'existe pas")
- À l'inscription : entreprise créée avec raison_sociale=nom_entreprise et
  siret placeholder "00000000000000" (à compléter via /parametres/entreprise
  après confirmation email + login)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Entreprise, User
from app.schemas.auth import (
    ConfirmEmailRequest,
    EmailRequest,
    RefreshRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserMe,
    UserRegister,
)
from app.services.auth_service import (
    AuthError,
    confirmation_email_expires_at,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_random_token,
    hash_password,
    password_reset_expires_at,
    verify_password,
)
from app.services.email_service import (
    send_confirmation_email,
    send_password_reset_email,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


def _now_utc() -> "datetime":
    """Helper local — évite l'import circulaire avec auth_service._now.

    Renvoie tz-aware UTC. Pour les comparaisons avec des datetime stockés
    en BDD (qui peuvent être naive en SQLite ou aware en Postgres), passer
    par `_is_expired()` qui normalise les deux côtés.
    """
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc)


def _is_expired(expires_dt) -> bool:
    """Compare un datetime stocké (peut-être tz-aware en Postgres ou naive
    en SQLite) avec maintenant. Robuste au mismatch tz introduit par
    SQLAlchemy DateTime(timezone=True) dont le comportement varie selon
    le dialect.

    Renvoie True si expires_dt est None OU < maintenant.
    """
    if expires_dt is None:
        return True
    from datetime import timezone
    now_aware = _now_utc()
    if expires_dt.tzinfo is None:
        # naive → traite comme UTC
        expires_aware = expires_dt.replace(tzinfo=timezone.utc)
    else:
        expires_aware = expires_dt
    return expires_aware < now_aware


def _build_user_me(user: User, entreprise: Entreprise) -> UserMe:
    return UserMe(
        id=user.id,
        email=user.email,
        nom_contact=user.nom_contact,
        entreprise_id=user.entreprise_id,
        nom_entreprise=entreprise.raison_sociale,
        is_admin=user.is_admin,
        is_active=user.is_active,
        date_creation=user.date_creation,
        date_derniere_connexion=user.date_derniere_connexion,
    )


def _issue_token_pair(user: User) -> TokenResponse:
    access, expires_in = create_access_token(user.id, user.entreprise_id)
    refresh = create_refresh_token(user.id, user.entreprise_id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
    )


# ---------------------------------------------------------------------------
# 1. Register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """Inscription self-service : crée Entreprise + User + envoie email de
    confirmation. is_active=False jusqu'à confirmation.
    """
    # Email unique check
    if db.query(User).filter(User.email == data.email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Crée l'entreprise (siret placeholder à compléter via /parametres
    # après confirmation + login)
    entreprise = Entreprise(
        raison_sociale=data.nom_entreprise,
        siret="00000000000000",
        is_demo=False,
    )
    db.add(entreprise)
    db.flush()  # génère entreprise.id pour la FK user

    # Crée l'utilisateur (is_active=False jusqu'à confirmation email)
    confirm_token = generate_random_token()
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        nom_contact=data.nom_contact,
        entreprise_id=entreprise.id,
        is_active=False,
        is_admin=False,
        email_confirmation_token=confirm_token,
        email_confirmation_expires=confirmation_email_expires_at(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Envoi email confirmation (no-op si SENDGRID_API_KEY absent — log dev)
    try:
        send_confirmation_email(user.email, user.nom_contact, confirm_token)
    except Exception:
        # On ne fait pas rollback de l'inscription si l'email échoue —
        # l'admin pourra réactiver manuellement ou l'utilisateur fera
        # /forgot-password. Le log est déjà fait dans email_service.
        pass

    return RegisterResponse(
        detail="Registration successful. Check your email to activate your account.",
        user_id=user.id,
        email=user.email,
    )


# ---------------------------------------------------------------------------
# 2. Login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Login email + password. Retourne access + refresh tokens."""
    user = db.query(User).filter(User.email == data.email).first()
    # Message identique pour user inconnu et password invalide (anti-enum)
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Confirm your email first.",
        )

    user.date_derniere_connexion = _now_utc()
    db.commit()

    return _issue_token_pair(user)


# ---------------------------------------------------------------------------
# 3. Logout (no-op stateless)
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout():
    """No-op stateless : le frontend clear localStorage. Endpoint exposé
    pour la cohérence API + futur logging d'audit (Sprint 13+)."""
    return {"detail": "Logged out"}


# ---------------------------------------------------------------------------
# 4. Confirm email
# ---------------------------------------------------------------------------


@router.post("/confirm-email", status_code=status.HTTP_200_OK)
def confirm_email(data: ConfirmEmailRequest, db: Session = Depends(get_db)):
    """Validation du token reçu par email à l'inscription.

    Set is_active=True + clear le token. Endpoint public (pas de
    Bearer requis — le user n'est pas encore loggable car is_active=False).
    """
    user = (
        db.query(User)
        .filter(User.email_confirmation_token == data.token)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation token",
        )
    if _is_expired(user.email_confirmation_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation token expired. Request a new one via /forgot-password.",
        )

    user.is_active = True
    user.email_confirmation_token = None
    user.email_confirmation_expires = None
    db.commit()
    return {"detail": "Email confirmed. You can now log in."}


# ---------------------------------------------------------------------------
# 5. Forgot password
# ---------------------------------------------------------------------------


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(data: EmailRequest, db: Session = Depends(get_db)):
    """Demande de reset password. Anti-enumeration : retourne toujours 200,
    même si l'email n'existe pas (pas de divulgation)."""
    user = db.query(User).filter(User.email == data.email).first()
    if user is not None:
        token = generate_random_token()
        user.password_reset_token = token
        user.password_reset_expires = password_reset_expires_at()
        db.commit()
        try:
            send_password_reset_email(user.email, user.nom_contact, token)
        except Exception:
            pass
    return {
        "detail": "If this email exists in our system, a reset link has been sent."
    }


# ---------------------------------------------------------------------------
# 6. Reset password
# ---------------------------------------------------------------------------


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(
    data: ResetPasswordRequest, db: Session = Depends(get_db)
):
    """Validation du token reçu par email + définition du nouveau password."""
    user = (
        db.query(User)
        .filter(User.password_reset_token == data.token)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )
    if _is_expired(user.password_reset_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token expired. Request a new one via /forgot-password.",
        )

    user.password_hash = hash_password(data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    return {"detail": "Password reset successful. You can now log in."}


# ---------------------------------------------------------------------------
# 7. /me — info user connecté (consommé par AuthContext frontend)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserMe)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Renvoie le user connecté + nom_entreprise (jointure)."""
    entreprise = db.query(Entreprise).filter(
        Entreprise.id == current_user.entreprise_id
    ).first()
    if entreprise is None:
        # Ne devrait jamais arriver (FK NOT NULL CASCADE), mais on log
        # explicitement.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entreprise associated to user not found",
        )
    return _build_user_me(current_user, entreprise)


# ---------------------------------------------------------------------------
# 8. Refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    """Échange un refresh_token contre une nouvelle paire access+refresh."""
    try:
        payload = decode_token(data.refresh_token, expected_type="refresh")
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token payload invalid",
        ) from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return _issue_token_pair(user)
