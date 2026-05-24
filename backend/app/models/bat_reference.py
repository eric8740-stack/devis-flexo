"""Modèle BatReference — Sprint 15 Lot 3 (FlexoCheck).

Un BAT (Bon À Tirer) validé client est attaché à un devis. Cette table
porte les métadonnées du BAT (URL stockage, mime, nom fichier, date
upload) ; le binaire est stocké via `photo_storage.save_photo()`
(Volume Railway local) et exposé via `GET /api/flexocheck/blobs/{key}`.

Cardinalité : 1 BAT par devis (`UNIQUE(devis_id)`). Le ré-upload remplace
l'existant — on conserve l'historique des binaires sur disque tant que
le devis vit, mais une seule row vivante en BDD.

Multi-tenant strict : `entreprise_id` NOT NULL FK CASCADE. La cascade
depuis le devis garantit que tout BAT survit ou s'éteint avec son devis.

Note V2 : migration vers Vercel Blob / Cloudflare R2 quand le projet
sortira du Volume Railway. L'attribut `bat_url` stocke alors une URL
publique externe au lieu d'une key locale.
"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


# MIME types autorisés à l'upload d'un BAT (cf. brief Sprint 15 Lot 3).
# PDF prioritaire (BAT pro), images en secours quand un client envoie une
# photo d'épreuve. SVG / RAW non supportés (encombrement, parsing risqué).
BAT_MIME_TYPES_AUTORISES = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/webp"}
)


class BatReference(Base):
    """BAT de référence d'un devis (1 par devis)."""

    __tablename__ = "bat_reference"
    __table_args__ = (
        Index("ix_bat_reference_entreprise", "entreprise_id"),
        UniqueConstraint("devis_id", name="uq_bat_reference_devis"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"), nullable=False
    )
    devis_id: Mapped[int] = mapped_column(
        ForeignKey("devis.id", ondelete="CASCADE"), nullable=False
    )

    # URL publique du BAT (côté MVP : "/api/flexocheck/blobs/{image_key}"
    # servie par le backend ; V2 : URL externe Vercel Blob / R2).
    bat_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Clé locale dans photo_storage (utilisée par GET /blobs/{key}).
    # Nullable pour rester compatible avec un futur stockage 100% externe.
    image_key: Mapped[str | None] = mapped_column(String(120))
    bat_filename: Mapped[str | None] = mapped_column(String(255))
    bat_mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bat_size_bytes: Mapped[int | None] = mapped_column(Integer)

    bat_uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Métadonnées validation client (optionnelles, remontées au moment
    # de l'upload si l'opérateur les connaît — sinon NULL).
    bat_date_validation: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    bat_valide_par: Mapped[str | None] = mapped_column(String(200))
