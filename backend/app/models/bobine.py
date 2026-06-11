"""Modèle Bobine — Module Stock S1 (option B, granularité A).

Granularité A : **1 ligne = 1 bobine PHYSIQUE unique** (emplacement + ml restant
propres). Module ADDITIF — n'est lu ni par le cost_engine, ni par bat_calculs,
ni par optimiser_pose, ni par /preview. Mouvements (S2) et lien devis↔stock (S3)
viendront plus tard.

Emplacement physique codé sur 3 champs `rangee` / `etage` / `position`, affiché
`A.0.25` (rangée A, étage 0, position 25) côté API (champ calculé `emplacement`).

Multi-tenant : `entreprise_id` NOT NULL FK CASCADE. `matiere_id` FK vers Matiere
(l'épaisseur est pré-remplie depuis la matière à la création, puis éditable).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Bobine(Base):
    __tablename__ = "bobine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Matière de la bobine. Pas d'ondelete (RESTRICT par défaut) : on ne supprime
    # pas une matière encore référencée par une bobine en stock.
    matiere_id: Mapped[int] = mapped_column(
        ForeignKey("matiere.id"), nullable=False, index=True
    )

    # Caractéristiques physiques. `epaisseur_microns` pré-rempli depuis la matière
    # à la création (cf. CRUD) puis éditable indépendamment.
    laize_mm: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    epaisseur_microns: Mapped[int | None] = mapped_column(Integer)

    # Métrage. `ml_initial` figé à la création = `ml_restant` initial ; `ml_restant`
    # éditable (les mouvements S2 le décrémenteront automatiquement plus tard).
    ml_initial: Mapped[int] = mapped_column(Integer, nullable=False)
    ml_restant: Mapped[int] = mapped_column(Integer, nullable=False)

    # Emplacement physique (codé A.0.25 = rangee.etage.position).
    rangee: Mapped[str] = mapped_column(String(10), nullable=False)
    etage: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # Cycle de vie. Défaut "en_stock" (S1) ; les statuts de consommation
    # viendront avec les mouvements (S2) et le lien devis↔stock (S3).
    statut: Mapped[str] = mapped_column(
        String(20), nullable=False, default="en_stock", server_default="en_stock"
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
