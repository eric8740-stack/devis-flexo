"""Modèle AnalysePhotoEtiquette — Sprint 13 Lot S13.E.2.

Stocke les résultats d'une analyse de photo d'étiquette par Claude API
multimodal (CdC § 03e). Une row par analyse, scopée tenant.

Cas d'usage métier : le commercial uploade la photo d'une étiquette
client existante pour estimer rapidement le nombre de couleurs, les
techniques d'impression visibles, et pré-remplir le formulaire de devis.

Champs principaux :
  - photo_url            : URL Vercel Blob (V2 — pour l'instant nullable)
  - photo_mime_type      : image/jpeg | image/png | image/webp | image/gif
  - resultats_ia         : JSON complet renvoyé par Claude (les 10 champs
                           du prompt + débriefs : couleurs_detectees,
                           techniques_impression_estimees, matiere_estimee,
                           finitions_visibles, niveau_confiance, etc.)
  - niveau_confiance     : extrait pour dénormalisation / index / requêtes
  - devis_id             : rattachement optionnel à un devis (nullable car
                           l'analyse peut être faite AVANT création du devis)

Multi-tenant : entreprise_id NOT NULL FK CASCADE.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AnalysePhotoEtiquette(Base):
    __tablename__ = "analyse_photo_etiquette"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Auteur de l'analyse (pour traçabilité audit + historique commercial)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    # Rattachement optionnel à un devis (peut être nul : analyse exploratoire)
    devis_id: Mapped[int | None] = mapped_column(
        ForeignKey("devis.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Métadonnées photo
    # photo_url : URL externe (Vercel Blob / R2 / ...) — vide en V1, gardé
    # nullable pour compat ascendante. Si un jour on migre vers un storage
    # externe (cf. notes Phase 2 prompt historique), cette colonne accueillera
    # l'URL signée.
    photo_url: Mapped[str | None] = mapped_column(String(500))
    photo_mime_type: Mapped[str | None] = mapped_column(String(30))

    # --- Feat historique analyses : stockage local Railway Volume ---------
    # image_filename : nom d'origine côté client (ex: "etiquette-bio.jpg"),
    #                  utile pour affichage UI et téléchargement.
    # image_key      : nom du fichier sur disque, format "{uuid}.{ext}".
    #                  UNIQUE car généré par UUID, sert de clé d'accès dans
    #                  GET /api/photos/{key}.
    # image_size_bytes : taille brute du fichier sauvé (pré-Claude). 0 si
    #                  upload disque a échoué (volume non monté, par ex.) —
    #                  l'analyse reste persistée, juste sans photo physique.
    image_filename: Mapped[str | None] = mapped_column(String(255))
    image_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    image_size_bytes: Mapped[int | None] = mapped_column(Integer)

    # Résultats Claude : JSON complet (les 10 champs CHAMPS_REQUIS du service)
    resultats_ia: Mapped[Any] = mapped_column(JSON, nullable=False)

    # Dénormalisation pour requêtes / index : extrait du resultats_ia
    niveau_confiance: Mapped[str | None] = mapped_column(String(10))
    nombre_couleurs_distinctes: Mapped[int | None] = mapped_column(Integer)

    # Tracking technique
    model_utilise: Mapped[str | None] = mapped_column(String(60))
    erreur: Mapped[str | None] = mapped_column(Text)  # NULL si analyse OK

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
