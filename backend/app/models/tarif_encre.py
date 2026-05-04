from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TarifEncre(Base):
    """Tarif encres par type technique : process_cmj, pantone, blanc_high_opaque, ...

    `type_encre` joue le rôle de clé symbolique (UNIQUE).
    `ratio_g_m2_couleur` est la consommation moyenne d'encre par m² et par couleur
    (défaut 2,000 g/m²/couleur).
    """

    __tablename__ = "tarif_encre"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py).
    # Note : `type_encre` UNIQUE devient cross-tenant car SQLite/Postgres
    # ne supportent pas UNIQUE conditionnel facilement — sera relâché en
    # composite UNIQUE (entreprise_id, type_encre) au S12-C si besoin.
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type_encre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    libelle: Mapped[str] = mapped_column(String(100), nullable=False)
    prix_kg_defaut: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    prix_kg_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    prix_kg_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ratio_g_m2_couleur: Mapped[Decimal] = mapped_column(
        Numeric(5, 3), nullable=False, default=Decimal("2.000")
    )
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
