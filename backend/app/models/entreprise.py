from decimal import Decimal

from sqlalchemy import Float, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

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

    # Paramètres calcul S3 — taux de chutes matière, ratio encre par couleur
    # et heures productives mensuelles globales (utilisées par le poste P7
    # frais généraux du moteur, en sus des heures presse/finition existantes
    # qui restent informatives côté UI).
    taux_chutes_defaut: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    ratio_encre_m2_couleur: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    heures_productives_mensuelles: Mapped[int | None] = mapped_column(Integer)
