"""Modèle MouvementStock — Module Stock S2 (journal d'audit des mouvements).

Journal append-only des mouvements de stock d'une bobine. `Bobine.ml_restant`
reste la source de vérité du métrage ; chaque mouvement l'ajuste
TRANSACTIONNELLEMENT (mouvement + bobine dans un seul commit) et garde la trace
`ml_avant` → `ml_apres` pour l'audit.

Types :
  - `entree`     : +ml (réception / retour)
  - `sortie`     : −ml (consommation ; refusée si ml > ml_restant, pas de négatif)
  - `inventaire` : corrige `ml_restant` à la valeur `ml` (audit ancien→nouveau)

Module ADDITIF — non lu par le cost_engine / bat_calculs / optimiser_pose /
devis / /preview. `devis_id` (nullable) sera renseigné en S3 (un devis confirmé
consomme le stock).

Multi-tenant : `entreprise_id` NOT NULL FK CASCADE. `bobine_id` FK CASCADE (la
suppression dure d'une bobine S1 emporte son historique). `devis_id` SET NULL.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MouvementStock(Base):
    __tablename__ = "mouvement_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bobine_id: Mapped[int] = mapped_column(
        ForeignKey("bobine.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # S3 — renseigné quand un devis confirmé consomme du stock (nullable en S2).
    devis_id: Mapped[int | None] = mapped_column(
        ForeignKey("devis.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Sens porté par le type ; `ml` toujours positif (quantité du mouvement, ou
    # nouvelle valeur cible pour un inventaire).
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    ml: Mapped[int] = mapped_column(Integer, nullable=False)

    # Audit : métrage restant avant / après application du mouvement.
    ml_avant: Mapped[int] = mapped_column(Integer, nullable=False)
    ml_apres: Mapped[int] = mapped_column(Integer, nullable=False)

    motif: Mapped[str | None] = mapped_column(String(200))
    reference: Mapped[str | None] = mapped_column(String(100))

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
