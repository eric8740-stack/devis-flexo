"""Modèle Bareme — Sprint 13 Lot S13.B.

Table générique pour stocker les **4 barèmes paramétrables** du moteur
d'optimisation, distingués par le champ `type` :

  - "echenillage"          : courbe intervalle dev → coefs vitesse/gâche
  - "effet_banane"         : table largeur plaque → développé cylindre mini
  - "confort_roulage"      : table rayon angles → coef vitesse + bonus quinconce
  - "compensation_laize_dev" : bonus opportunité quand laize ≥ seuil

Le CdC propose 3 tables séparées (tables_echenillage, baremes_effet_banane,
baremes_confort_roulage). On unifie en UNE seule table générique pour
KISS et faciliter l'UI de paramétrage (1 page, 1 dropdown type, 1
éditeur JSON). Le contenu structuré du barème vit dans le champ
`bareme_data` JSONB, schéma libre selon le type.

Multi-tenant : entreprise_id NOT NULL FK CASCADE. Chaque imprimerie
ajuste ses 4 barèmes selon son parc (presses récentes vs anciennes,
matières dominantes, etc.). Le seed Sprint 13 livre les 4 defaults
ICE comme point de départ.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Types de barèmes supportés. Aligné avec les règles 2/3/4/5 du moteur.
BAREME_TYPES = frozenset(
    {"echenillage", "effet_banane", "confort_roulage", "compensation_laize_dev"}
)


class Bareme(Base):
    __tablename__ = "bareme"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Discriminant — l'app valide via BAREME_TYPES côté service.
    # On n'utilise pas Enum SQL pour rester portable SQLite/PostgreSQL et
    # faciliter l'ajout de nouveaux types Sprint 14+ sans migration ALTER.
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    nom: Mapped[str | None] = mapped_column(String(100))

    # Optionnel : liste des machine_imprimerie.id auxquelles ce barème
    # s'applique. Null = applicable à toutes les machines de l'entreprise.
    # Permet à un imprimeur d'avoir 2 barèmes échenillage différents pour
    # une presse récente vs une presse de 1995.
    applicable_aux_machines: Mapped[list[int] | None] = mapped_column(JSON)

    # Contenu structuré du barème. Schéma par type :
    #   echenillage : [{intervalle_max_mm, qualite, coef_vitesse, coef_gache, score}]
    #   effet_banane : [{largeur_max_mm, developpe_mini_mm}]
    #   confort_roulage : {rayon: [...], quinconce_bonus_pct: 10}
    #   compensation_laize_dev : [{intervalle_dev_max_mm, laize_requise_mm, bonus_vitesse_pct}]
    bareme_data: Mapped[Any] = mapped_column(JSON, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
