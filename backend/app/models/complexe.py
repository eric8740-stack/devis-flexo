from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
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


class Complexe(Base):
    """Complexe adhésif (matière des étiquettes).

    `prix_m2_eur` est la donnée critique pour le poste P1 du moteur de
    calcul S3 : coût matière = surface_totale × prix_m2.
    """

    __tablename__ = "complexe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reference: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # bopp / pp / pe / pvc_vinyle / thermique / papier_couche /
    # papier_standard / papier_epais / papier_kraft / papier_verge
    famille: Mapped[str] = mapped_column(String(50), nullable=False)

    face_matiere: Mapped[str | None] = mapped_column(String(150))
    grammage_g_m2: Mapped[int | None] = mapped_column(Integer)
    adhesif_type: Mapped[str | None] = mapped_column(String(50))

    prix_m2_eur: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    fournisseur_id: Mapped[int | None] = mapped_column(
        ForeignKey("fournisseur.id", ondelete="SET NULL")
    )

    # Sprint 9 v2 : refactor `statut` String ('actif'/'archive') → `actif` Boolean
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    commentaire: Mapped[str | None] = mapped_column(Text)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
