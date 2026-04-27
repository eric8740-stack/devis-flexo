from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PartenaireST(Base):
    """Partenaire sous-traitance finition (différent des fournisseurs matière)."""

    __tablename__ = "partenaire_st"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    raison_sociale: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True
    )
    siret: Mapped[str | None] = mapped_column(String(14))

    contact_nom: Mapped[str | None] = mapped_column(String(100))
    contact_email: Mapped[str | None] = mapped_column(String(150))
    contact_tel: Mapped[str | None] = mapped_column(String(30))

    # finition / decoupe / dorure / autre
    prestation_type: Mapped[str | None] = mapped_column(String(20))

    delai_jours_moyen: Mapped[int | None] = mapped_column(Integer)
    qualite_score: Mapped[int | None] = mapped_column(Integer)  # 1 à 5

    commentaire: Mapped[str | None] = mapped_column(Text)
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
