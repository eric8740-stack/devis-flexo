from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Client(Base):
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    raison_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    siret: Mapped[str | None] = mapped_column(String(14))

    adresse_fact: Mapped[str | None] = mapped_column(String(255))
    cp_fact: Mapped[str | None] = mapped_column(String(10))
    ville_fact: Mapped[str | None] = mapped_column(String(100))

    contact: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    tel: Mapped[str | None] = mapped_column(String(30))

    segment: Mapped[str | None] = mapped_column(String(50))
    date_creation: Mapped[date | None] = mapped_column(Date)
