"""Service d'authentification — Sprint 12 multi-tenant.

Centralise :
- Hash + vérification password via passlib bcrypt
- Encode + décode JWT (access + refresh) via python-jose, HS256
- Génération de tokens random URL-safe pour emails (confirmation + reset)
- Decode robuste : raise `AuthError` typés (expired, invalid, missing)

Pas de table session côté serveur — refresh JWT stateless. Si Eric veut
révoquer en bloc : changer JWT_SECRET en prod (invalide tous les tokens).
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration JWT (env vars Railway en prod, fallback dev avec WARNING)
# ---------------------------------------------------------------------------

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "60")
)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))


def _resolve_jwt_secret() -> str:
    """Lit JWT_SECRET en env. Fallback dev avec WARNING explicite."""
    secret = os.getenv("JWT_SECRET")
    if secret is None:
        logger.warning(
            "JWT_SECRET env var not set — using fallback 'dev-secret-change-me'. "
            "ANYONE WHO READS THE CODE CAN FORGE TOKENS. "
            "CHANGE IN PRODUCTION via Railway env var (openssl rand -hex 64)."
        )
        return "dev-secret-change-me"
    return secret


# Lecture lazy : une seule fois à l'import du module. Si JWT_SECRET change
# (rotation), il faut redémarrer l'app.
JWT_SECRET = _resolve_jwt_secret()

# ---------------------------------------------------------------------------
# Hash password (bcrypt via passlib)
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash bcrypt d'un password en clair. Coût par défaut (12 rounds)."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Compare un password en clair à un hash bcrypt. False si invalide."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT access + refresh
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Erreur d'authentification — encapsule les cas JWT invalide / expiré."""


def _now() -> datetime:
    """UTC tz-aware — utilisé pour les timestamps JWT (iat/exp).

    ATTENTION : `datetime.timestamp()` sur un naive interprète en local
    time → mauvais Unix timestamp. Il faut donc `_now()` tz-aware pour
    encoder les JWT. Pour les datetime stockés en BDD (expires email/reset),
    on convertit explicitement via `_naive_now()` pour éviter le mismatch
    aware/naive sur SQLite (cf. `_is_expired()` côté router pour la
    comparaison robuste).
    """
    return datetime.now(tz=timezone.utc)


def _naive_now() -> datetime:
    """UTC naive — pour les datetime stockés en BDD (expires email/reset).
    Cohérent avec ce que SQLite renvoie."""
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


def _encode_jwt(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int, entreprise_id: int) -> tuple[str, int]:
    """Crée un JWT access token. Retourne (token, expires_in_seconds)."""
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = {
        "sub": str(user_id),
        "entreprise_id": entreprise_id,
        "type": "access",
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(seconds=expires_in)).timestamp()),
    }
    return _encode_jwt(payload), expires_in


def create_refresh_token(user_id: int, entreprise_id: int) -> str:
    """Crée un JWT refresh token (durée plus longue)."""
    payload = {
        "sub": str(user_id),
        "entreprise_id": entreprise_id,
        "type": "refresh",
        "iat": int(_now().timestamp()),
        "exp": int(
            (_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()
        ),
    }
    return _encode_jwt(payload)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Décode un JWT et retourne le payload. Lève `AuthError` si invalide.

    `expected_type` : "access" | "refresh" | None (pas de check de type).
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise AuthError(f"Invalid or expired token: {exc}") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthError(
            f"Token type mismatch: expected {expected_type!r}, "
            f"got {payload.get('type')!r}"
        )
    return payload


# ---------------------------------------------------------------------------
# Tokens random pour emails (confirmation + reset password)
# ---------------------------------------------------------------------------


def generate_random_token(nbytes: int = 32) -> str:
    """Token URL-safe pour confirmation email / reset password.

    32 bytes → 43 chars en base64 URL-safe (entropie cryptographique).
    Stocké en BDD User (email_confirmation_token / password_reset_token)
    avec un timestamp d'expiration séparé.
    """
    return secrets.token_urlsafe(nbytes)


def confirmation_email_expires_at() -> datetime:
    """Email confirmation : valide 24h après l'inscription. Naive UTC."""
    return _naive_now() + timedelta(hours=24)


def password_reset_expires_at() -> datetime:
    """Password reset : valide 1h après la demande. Naive UTC."""
    return _naive_now() + timedelta(hours=1)
