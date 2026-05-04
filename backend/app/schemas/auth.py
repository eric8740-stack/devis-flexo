"""Schémas Pydantic — auth Sprint 12.

`extra="forbid"` partout pour rejeter les champs accessoires (sécurité).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class UserRegister(BaseModel):
    """Body POST /api/auth/register — inscription self-service."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nom_entreprise: str = Field(min_length=2, max_length=150)
    nom_contact: str = Field(min_length=2, max_length=150)


class UserLogin(BaseModel):
    """Body POST /api/auth/login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class EmailRequest(BaseModel):
    """Body POST /api/auth/forgot-password."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ConfirmEmailRequest(BaseModel):
    """Body POST /api/auth/confirm-email."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=10, max_length=255)


class ResetPasswordRequest(BaseModel):
    """Body POST /api/auth/reset-password."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=10, max_length=255)
    new_password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    """Body POST /api/auth/refresh."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=10)


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    """Sortie /login + /refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # secondes


class UserMe(BaseModel):
    """Sortie GET /api/auth/me — info user connecté pour AuthContext."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom_contact: str
    entreprise_id: int
    nom_entreprise: str
    is_admin: bool
    is_active: bool
    date_creation: datetime
    date_derniere_connexion: datetime | None


class RegisterResponse(BaseModel):
    """Sortie /register — pas de tokens (l'utilisateur doit confirmer email)."""

    detail: str
    user_id: int
    email: str
