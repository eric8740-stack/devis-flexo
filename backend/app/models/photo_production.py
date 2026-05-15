"""Modèle PhotoProduction — Sprint 13 Lot S13.F.

Table générique pour TOUTES les photos prises pendant un run production,
quel que soit leur rôle :

  - 1er_tirage          : photo BAT vs 1er tirage (validation démarrage)
  - controle_continu    : photos prises en cours d'impression (toutes les
                          N minutes ou N bobines, paramétrable)
  - finition            : photo après dorure / vernis / découpe spéciale
  - bobine_finie        : photo bobine en sortie de rebobineuse
  - palette_face        : photo de face d'une palette finie
  - palette_dessus      : photo dessus d'une palette finie
  - etiquette_palette   : photo de l'étiquette palette (n° lot, SSCC...)

Approche "1 table générique + discriminator type_etape" plutôt que 7
tables séparées : plus simple à étendre (nouveau type = nouvelle valeur
de string + règle métier), plus simple à requêter (timeline globale d'un
run = SELECT * WHERE devis_id ORDER BY photo_timestamp).

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
rapport_qualite_id : NULLABLE (les photos peuvent exister avant
rattachement à un rapport finalisé).

Note : workflows API + capture mobile + IA = Sprint 14/15. Ici on
matérialise UNIQUEMENT la table.

Conventions projet appliquées vs CdC :
  - UUID → Integer autoincrement
  - company_id → entreprise_id
  - devis_specs_id → devis_id (table existante)
  - users(id) → user.id (singulier dans notre projet)
  - JSONB → JSON
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
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


# Valeurs autorisées pour photo_production.type_etape — validé app-side.
# Pas de CHECK constraint SQL pour rester compatible SQLite (et garder
# l'extensibilité V2 sans migration).
PHOTO_TYPE_ETAPES = frozenset(
    {
        "1er_tirage",
        "controle_continu",
        "finition",
        "bobine_finie",
        "palette_face",
        "palette_dessus",
        "etiquette_palette",
    }
)


class PhotoProduction(Base):
    __tablename__ = "photo_production"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    devis_id: Mapped[int] = mapped_column(
        ForeignKey("devis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rapport_qualite_id: Mapped[int | None] = mapped_column(
        ForeignKey("rapport_qualite_production.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Type discriminator — valeurs dans PHOTO_TYPE_ETAPES
    type_etape: Mapped[str] = mapped_column(String(30), nullable=False)

    # Métadonnées photo
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    photo_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    operateur_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    # Données spécifiques selon le type
    reference_url: Mapped[str | None] = mapped_column(Text)
    resultats_analyse_ia: Mapped[Any | None] = mapped_column(JSON)
    score_conformite: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ecarts_detectes: Mapped[Any | None] = mapped_column(JSON)

    # Spécifique palettes
    numero_palette: Mapped[int | None] = mapped_column(Integer)
    nb_bobines_palette: Mapped[int | None] = mapped_column(Integer)
    poids_palette_kg: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    etiquette_palette_data: Mapped[Any | None] = mapped_column(JSON)

    # Validation
    # valide | valide_avec_reserves | rejete
    decision_finale: Mapped[str | None] = mapped_column(String(30))
    motif_decision: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
