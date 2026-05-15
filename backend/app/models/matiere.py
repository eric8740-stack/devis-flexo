"""Modèle Matiere — Sprint 13 Lot S13.B.

Catalogue matières (papiers, films, thermiques, syntétiques) au format
moteur d'optimisation. Coexiste avec la table existante `complexe`
(Sprint 2) qui continue d'alimenter le moteur de coûts historique.

Différences vs `complexe` existant :
  - `est_transparent` (Boolean) — déclenche automatiquement la règle
    métier "spot de détection verso obligatoire" dans le moteur
    d'optimisation Sprint 13
  - `opacite_pct` (Numeric 4,1) — 100 = opaque total, 0 = transparent
  - `certifications_sanitaires` / `certifications_env` (JSON) — filtres
    pharma/agro/cosmétique (FDA, FSC, EU 10/2011…)
  - `fournisseurs` (JSON) — array de {frns_id, prix_m2, mini_cmde, ref}
    pour gérer le multi-sourcing au sein d'une seule fiche matière

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Matiere(Base):
    __tablename__ = "matiere"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identification
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    libelle: Mapped[str] = mapped_column(String(200), nullable=False)
    categorie: Mapped[str | None] = mapped_column(String(50))
    sous_type: Mapped[str | None] = mapped_column(String(50))

    # Caractéristiques physiques (au moins l'un des deux requis en pratique)
    grammage_gm2: Mapped[int | None] = mapped_column(Integer)
    epaisseur_microns: Mapped[int | None] = mapped_column(Integer)

    # Compatibilités adhésifs (ex: ["permanent", "contact_alimentaire"])
    adhesifs_compatibles: Mapped[list[str] | None] = mapped_column(JSON)

    # Transparence — déclenche la règle "spot de détection verso obligatoire"
    # dans le moteur d'optimisation (cf. Section 5 INSTRUCTIONS — Spot
    # de détection verso pour matières transparentes).
    est_transparent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    opacite_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))

    # Certifications — filtres pharma/agro/cosmétique
    certifications_sanitaires: Mapped[list[str] | None] = mapped_column(JSON)
    certifications_env: Mapped[list[str] | None] = mapped_column(JSON)

    # Multi-sourcing : array de {frns_id, prix_m2, mini_cmde, ref_fournisseur}
    fournisseurs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)

    notes_techniques: Mapped[str | None] = mapped_column(Text)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
