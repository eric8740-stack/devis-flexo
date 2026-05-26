from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Client(Base):
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (NOT NULL strict côté
    # BDD, injection user.entreprise_id en S12-C). Backfill migration → 1
    # pour tous les records existants (compte demo Eric).
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

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

    # Sprint 16 — profil rebobinage client (caractérise les contraintes
    # presse-aval du client : mandrin, bobine, marquage, conditionnement).
    # Tous rétro-compatibles : nullable côté Integer/String, et Boolean
    # NOT NULL avec `default=False` côté ORM Python + `server_default
    # sa.false()` côté migration (les ~20 clients seedés du compte demo
    # reçoivent FALSE au upgrade).
    # `sens_enroulement` est un entier 1..8 (convention SE1-SE8, cf.
    # `app/services/rotation_se.py` — lecture seule). Stocké comme info
    # client à ce stade ; sa consommation par le moteur (cohérence sens)
    # est gated derrière un test métier en cours (hors scope ici).
    diametre_mandrin_mm: Mapped[int | None] = mapped_column(Integer)
    diametre_max_bobine_mm: Mapped[int | None] = mapped_column(Integer)
    sens_enroulement: Mapped[int | None] = mapped_column(Integer)
    nb_etiq_par_bobine_fixe: Mapped[int | None] = mapped_column(Integer)
    marquage_bobine_requis: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    marquage_bobine_format: Mapped[str | None] = mapped_column(String(100))
    mandrin_fourni_par_client: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    film_protection_requis: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    conditionnement_souhaite: Mapped[str | None] = mapped_column(String(100))
