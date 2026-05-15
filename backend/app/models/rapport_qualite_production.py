"""Modèle RapportQualiteProduction — Sprint 13 Lot S13.F.

Fondation DB pour FlexoCheck (module IA qualité). Stocke les rapports
de production multi-étapes générés en fin de run, avec :

  - Statut (en_construction / finalise / envoye_client)
  - Archivage PDF (URL Vercel Blob + hash SHA-256 valeur probante)
  - Timestamps par étape (impression / finition / rebobinage /
    conditionnement) + durées calculées → identification goulots
  - Diffusion paramétrable (interne / envoi_auto / lien_temps_reel /
    lien_validation) avec token public + expiration
  - Stats agrégées (nb contrôles, écarts majeurs/mineurs, score moyen)

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
devis_id NOT NULL : un rapport est toujours rattaché à un devis (run).

Note : workflows API + génération PDF + IA = Sprint 14/15. Ici on
matérialise UNIQUEMENT la table pour que les futurs sprints aient déjà
la fondation DB en prod sans nouvelle migration.

Conventions projet appliquées vs CdC :
  - UUID → Integer autoincrement
  - company_id → entreprise_id (FK entreprise.id CASCADE)
  - devis_specs_id → devis_id (table existante)
  - JSONB → JSON
  - Single CREATE incluant les colonnes du ALTER d'extension
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RapportQualiteProduction(Base):
    __tablename__ = "rapport_qualite_production"

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

    # État du rapport — en_construction | finalise | envoye_client
    statut: Mapped[str | None] = mapped_column(String(20))

    # Archivage PDF
    pdf_url: Mapped[str | None] = mapped_column(String(500))
    pdf_genere_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pdf_hash_sha256: Mapped[str | None] = mapped_column(String(64))

    # Timestamps de production (rapport global)
    production_debut_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    production_fin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duree_production_min: Mapped[int | None] = mapped_column(Integer)
    duree_estimee_min: Mapped[int | None] = mapped_column(Integer)
    ecart_temps_estime_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Diffusion
    # interne | envoi_auto | lien_temps_reel | lien_validation
    mode_diffusion: Mapped[str | None] = mapped_column(String(30))
    email_client_envoye_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    lien_public_token: Mapped[str | None] = mapped_column(String(100))
    lien_public_expire_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Stats agrégées
    nb_controles_total: Mapped[int | None] = mapped_column(Integer)
    nb_ecarts_majeurs: Mapped[int | None] = mapped_column(Integer)
    nb_ecarts_mineurs: Mapped[int | None] = mapped_column(Integer)
    nb_retirages_necessaires: Mapped[int | None] = mapped_column(Integer)
    score_moyen_conformite: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    validation_finale: Mapped[str | None] = mapped_column(String(30))

    # Archivage paramétrable
    duree_conservation_ans: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    archive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Extension : timestamps par étape + durées calculées ------------
    # (cf. CdC § "Extension rapports_qualite_production" — inclus directement
    # dans le CREATE plutôt que via ALTER pour simplifier la migration)
    impression_debut_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    impression_fin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finition_debut_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finition_fin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rebobinage_debut_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    rebobinage_fin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    conditionnement_debut_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    conditionnement_fin_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    duree_impression_min: Mapped[int | None] = mapped_column(Integer)
    duree_finition_min: Mapped[int | None] = mapped_column(Integer)
    duree_rebobinage_min: Mapped[int | None] = mapped_column(Integer)
    duree_conditionnement_min: Mapped[int | None] = mapped_column(Integer)
    duree_totale_chaine_min: Mapped[int | None] = mapped_column(Integer)

    nb_palettes_total: Mapped[int | None] = mapped_column(Integer)
    nb_palettes_validees: Mapped[int | None] = mapped_column(Integer)

    # Goulot d'étranglement (V2) — string libre :
    # impression | finition | rebobinage | conditionnement
    etape_la_plus_longue: Mapped[str | None] = mapped_column(String(30))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
