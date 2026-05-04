from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChargeMensuelle(Base):
    """Frais fixes mensuels (loyer, salaires, énergie, ...).

    Sert à calculer le coût horaire de la structure (S3, poste P3 et P4).
    """

    __tablename__ = "charge_mensuelle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    libelle: Mapped[str] = mapped_column(String(150), nullable=False)

    # loyer / salaires / energie / assurance / fournitures / autre
    categorie: Mapped[str] = mapped_column(String(30), nullable=False)

    montant_eur: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    # NULL = en cours
    date_fin: Mapped[date | None] = mapped_column(Date)

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
