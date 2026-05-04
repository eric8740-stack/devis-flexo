from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Entreprise(Base):
    __tablename__ = "entreprise"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    raison_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    siret: Mapped[str] = mapped_column(String(14), nullable=False)

    adresse: Mapped[str | None] = mapped_column(String(255))
    cp: Mapped[str | None] = mapped_column(String(10))
    ville: Mapped[str | None] = mapped_column(String(100))
    tel: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))

    pct_fg: Mapped[float | None] = mapped_column(Float)
    pct_marge_defaut: Mapped[float | None] = mapped_column(Float)
    heures_prod_presse_mois: Mapped[int | None] = mapped_column(Integer)
    heures_prod_finition_mois: Mapped[int | None] = mapped_column(Integer)

    # Sprint 12 multi-tenant : flag pour identifier le compte démo Eric
    # (qui hérite des 148 records seedés). Les nouvelles entreprises créées
    # via inscription ont is_demo=False et démarrent avec un espace vierge.
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relation 1-to-1 vers User (back_populates de User.entreprise)
    user = relationship(
        "User", back_populates="entreprise", uselist=False, cascade="all, delete-orphan"
    )
