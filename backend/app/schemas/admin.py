"""Schémas Pydantic /api/admin (Sprint 12 Lot S12-D).

Réservé aux endpoints administrateur (Eric / `is_admin=True`). La
création manuelle d'un compte par admin court-circuite le flux
d'inscription email (pas de confirmation, `is_active=True` direct).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserRead(BaseModel):
    """Vue d'un user pour l'admin — joint nom_entreprise + is_demo."""

    id: int
    email: str
    nom_contact: str
    is_active: bool
    is_admin: bool
    entreprise_id: int
    nom_entreprise: str
    is_demo: bool
    date_creation: datetime
    date_derniere_connexion: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AdminUserCreate(BaseModel):
    """Payload de création manuelle d'un compte par admin.

    Contrairement à `/api/auth/register` :
    - pas d'email de confirmation (validé manuellement par Eric)
    - `is_active=True` immédiatement
    - création atomique Entreprise + User dans la même transaction
    """

    email: EmailStr
    password: str = Field(min_length=8)
    nom_entreprise: str = Field(min_length=2, max_length=150)
    nom_contact: str = Field(min_length=2, max_length=150)
    is_admin: bool = False

    model_config = ConfigDict(extra="forbid")
