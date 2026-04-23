from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Fournisseur(Base):
    __tablename__ = "fournisseur"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    raison_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    categorie: Mapped[str | None] = mapped_column(String(50))

    contact: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    tel: Mapped[str | None] = mapped_column(String(30))

    conditions_paiement: Mapped[str | None] = mapped_column(String(100))
    delai_livraison_j: Mapped[int | None] = mapped_column(Integer)
