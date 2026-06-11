from decimal import Decimal

from sqlalchemy import Boolean, Float, Integer, Numeric, String
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

    # PR #9.1 — 4 paramètres BAT (Bon À Tirer / FlexoCompare).
    # Pilotent les calculs d'implantation affichés sur /optimisation.
    # Defaults ICE Étiquettes (28 ans d'expertise Eric Paysant) ; les
    # imprimeurs pilotes peuvent les ajuster via Paramètres > Entreprise.
    chute_laterale_min_mm: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("10.00")
    )
    palier_laize_papier_mm: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )
    refilage_systematique: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    marge_liner_mm: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("2.50")
    )

    # Lot F — mode de livraison bobine par défaut (ml de matière par bobine
    # livrée). Sert au bloc bobinage/appro de /preview (géométrie seule, AUCUN
    # chiffrage). 2000 = standard ; 1000/4000 selon le client, surchargeable par
    # requête (`ml_par_bobine`) ou via Paramètres > Entreprise.
    ml_par_bobine_defaut: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2000, server_default="2000"
    )

    # Sprint 12 multi-tenant : flag pour identifier le compte démo Eric
    # (qui hérite des 148 records seedés). Les nouvelles entreprises créées
    # via inscription ont is_demo=False et démarrent avec un espace vierge.
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relation 1-to-1 vers User (back_populates de User.entreprise)
    user = relationship(
        "User", back_populates="entreprise", uselist=False, cascade="all, delete-orphan"
    )
