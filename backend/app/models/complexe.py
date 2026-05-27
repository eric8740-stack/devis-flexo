from datetime import datetime
from decimal import Decimal

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
    # Lot 1 complexe enrichi : Integer → Numeric(5,1). Les films ont un
    # grammage de FACE dérivé (épaisseur × densité) non entier (ex. BOPP
    # 50µ × 0.91 = 45.5 g/m²). Cohérent avec le grammage de face des papiers.
    grammage_g_m2: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    adhesif_type: Mapped[str | None] = mapped_column(String(50))

    prix_m2_eur: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    # Lot 1 complexe enrichi — champs lus / filtrés par le moteur d'optimisation
    # (alignés sur la table `matiere` pour préparer le pont matière↔complexe).
    # epaisseur_microns : films uniquement (NULL pour les papiers, qui se
    #   caractérisent au grammage). sous_type : granularité sous la famille.
    # est_transparent : déclenche la règle "spot de détection verso". opacite_pct :
    #   100 = opaque total, 0 = transparent. certifications_* : filtres pharma/agro.
    epaisseur_microns: Mapped[int | None] = mapped_column(Integer)
    est_transparent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    opacite_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    sous_type: Mapped[str | None] = mapped_column(String(50))
    certifications_sanitaires: Mapped[list[str] | None] = mapped_column(JSON)
    certifications_env: Mapped[list[str] | None] = mapped_column(JSON)

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
