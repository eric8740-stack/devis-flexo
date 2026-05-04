from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Catalogue(Base):
    """Produit récurrent d'un client (nomenclature).

    Pré-remplit un devis quand un client recommande un produit déjà chiffré.
    """

    __tablename__ = "catalogue"
    __table_args__ = (
        UniqueConstraint(
            "code_produit", "client_id", name="uq_catalogue_code_client"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code_produit: Mapped[str] = mapped_column(String(50), nullable=False)
    designation: Mapped[str] = mapped_column(String(200), nullable=False)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("client.id", ondelete="RESTRICT"), nullable=False
    )
    machine_id: Mapped[int | None] = mapped_column(
        ForeignKey("machine.id", ondelete="SET NULL")
    )

    matiere: Mapped[str | None] = mapped_column(String(100))
    format_mm: Mapped[str | None] = mapped_column(String(50))
    nb_couleurs: Mapped[int | None] = mapped_column(Integer)
    prix_unitaire_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # ponctuelle / mensuelle / trimestrielle / annuelle
    frequence_estimee: Mapped[str | None] = mapped_column(String(20))

    commentaire: Mapped[str | None] = mapped_column(Text)
    # actif / archive
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="actif")

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
