from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TarifPoste(Base):
    """Paramètre tarifaire d'un poste de coût (1 à 7).

    Identifié par une clé symbolique snake_case (`matiere_prix_kg_defaut`,
    `marge_confort_roulage_mm`, ...) — le moteur de calcul accède toujours
    via `repo.get_by_cle("...")`, jamais par libellé.
    """

    __tablename__ = "tarif_poste"
    __table_args__ = (
        CheckConstraint(
            "poste_numero BETWEEN 1 AND 7", name="ck_tarif_poste_poste_numero"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    cle: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    poste_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    valeur_defaut: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    valeur_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    valeur_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    unite: Mapped[str] = mapped_column(String(30), nullable=False)
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
