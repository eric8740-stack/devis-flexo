"""Modèle User — Sprint 12 multi-tenant.

Un utilisateur authentifié, lié 1-to-1 à une entreprise (1 user = 1 espace
de données pour MVP). L'auth utilise JWT stateless (Bearer header) avec
hash bcrypt pour les passwords.

Tokens email (confirmation + reset password) stockés en BDD avec expiration.
Pas de table session : refresh_token JWT stateless également (à raffiner
Sprint 13/14 si besoin de révocation côté serveur).
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nom_contact: Mapped[str] = mapped_column(String(150), nullable=False)

    # Relation 1-to-1 entreprise (UNIQUE FK pour MVP)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    entreprise = relationship("Entreprise", back_populates="user", uselist=False)

    # Statut compte
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Sprint 13 Lot S13.A — Activation modulaire FlexoSuite.
    # has_flexocompare : module devis intelligent (cœur historique)
    # has_flexocheck   : module IA qualité standalone (BAT, photo, rapport)
    # Default True à la création = bundle FlexoSuite (révisable Sprint 18
    # lors de l'ouverture commerciale Stripe avec ?module=... à l'inscription).
    has_flexocompare: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    has_flexocheck: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Tokens email
    email_confirmation_token: Mapped[str | None] = mapped_column(String(255))
    email_confirmation_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    password_reset_token: Mapped[str | None] = mapped_column(String(255))
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Timestamps
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_derniere_connexion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # ------------------------------------------------------------------
    # Propriétés dérivées Sprint 13 — pratiques pour UI / debug / logs
    # ------------------------------------------------------------------

    @property
    def has_bundle(self) -> bool:
        """True si l'utilisateur dispose des deux modules (= bundle FlexoSuite)."""
        return self.has_flexocompare and self.has_flexocheck

    @property
    def active_modules(self) -> list[str]:
        """Liste sérialisable des modules actifs — utile pour /api/auth/me."""
        modules: list[str] = []
        if self.has_flexocompare:
            modules.append("flexocompare")
        if self.has_flexocheck:
            modules.append("flexocheck")
        return modules
