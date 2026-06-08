"""Modèle LotProduction — un lot de production d'un devis multi-lots.

Sprint 13 avenant — refonte optim pose multi-lots.

Convention métier : un devis peut être fractionné en N lots de production
avec configurations différentes (ex : urgence client → matière A pour
10 000 étiquettes puis matière B pour 5 000 suivantes). Le moteur cost_engine
est appelé N fois, une fois par lot, sans modification de sa logique
interne (sacred invariant).

Multi-tenant scoping : entreprise_id obligatoire (CASCADE), même pattern
que les autres tables. Le CRUD doit utiliser get_or_404_scoped pour
prévenir l'énumération inter-tenant.

PK Integer autoincrement, FK singuliers ("cylindre_magnetique.id" etc.)
conformes à la convention projet (cf. devis.py, matiere.py).
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LotProduction(Base):
    """Un lot de production rattaché à un devis (1..N par devis).

    Chaque lot porte sa propre config moteur (cylindre, machine, poses,
    sens enroulement) + matière + quantité, et caches ses résultats
    calculés (intervalles, score, coût) pour PDF / historique sans
    rappeler cost_engine à chaque rendu.
    """

    __tablename__ = "lot_production"
    __table_args__ = (
        Index("ix_lot_production_devis", "devis_id"),
        Index("ix_lot_production_entreprise", "entreprise_id"),
        UniqueConstraint("devis_id", "ordre", name="uq_lot_production_devis_ordre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    devis_id: Mapped[int] = mapped_column(
        ForeignKey("devis.id", ondelete="CASCADE"), nullable=False
    )
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position dans le devis (1, 2, 3, ...). Unique par devis_id.
    ordre: Mapped[int] = mapped_column(Integer, nullable=False)

    # Config production (issue d'un candidat moteur optim).
    # Lot back A : NULLABLE — un lot « mode sans outil » n'a PAS d'outil de
    # découpe (cylindre), il imprime pleine largeur puis refend.
    cylindre_id: Mapped[int | None] = mapped_column(
        ForeignKey("cylindre_magnetique.id"), nullable=True
    )
    # P1+P2 : FK rebascule vers `machine.id` (parc unique post-fusion
    # MI -> Machine, cf migration b2c3d4e5f6g7).
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machine.id"), nullable=False
    )
    nb_poses_dev: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_poses_laize: Mapped[int] = mapped_column(Integer, nullable=False)

    # Sens enroulement : 1 à 8 (convention métier flexographique).
    # Mapping libellés / rotations dans app/services/rotation_se.py (sacred).
    sens_enroulement: Mapped[int] = mapped_column(Integer, nullable=False)

    # Quantité du lot + matière (FK NOT NULL — chaque lot a sa matière).
    quantite: Mapped[int] = mapped_column(Integer, nullable=False)
    matiere_id: Mapped[int] = mapped_column(
        ForeignKey("matiere.id"), nullable=False
    )

    # Résultats calculés cachés (snapshot du moteur au moment de la création).
    intervalle_dev_reel_mm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    intervalle_laize_reel_mm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    largeur_plaque_mm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    # L1 (géométrie laize) — bord latéral SYMÉTRIQUE surchargeable par côté
    # (mm). NULL → défaut = `entreprise.chute_laterale_min_mm` (comportement
    # actuel préservé). Pilote la laize papier déterministe (plaque + 2×bord).
    # Concept SÉPARÉ des lacets (intervalle/2) qui restent intouchés. Asymétrie
    # g/d hors L1. NON consommé par P1 (cost_engine intouché).
    bord_lateral_mm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Lot back A — mode « format sans outil » (impression pleine largeur +
    # refente). Défaut False (server_default) → tout lot existant reste un lot
    # avec outil (value-neutral). `laize_stock_mm` = bobine mère facturée par
    # P1 quand le mode est actif (NULL sinon).
    mode_sans_outil: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    laize_stock_mm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    # Lot back B — override opérateur du nb de bobines filles de refente
    # (souveraineté lot back A). NULL → nb_filles dérivé de la géométrie. C'est
    # la SOURCE du nb_filles résolu (≠ `nb_poses_laize`, qui est l'axe poses).
    nb_filles_force: Mapped[int | None] = mapped_column(Integer)

    score_optim: Mapped[float | None] = mapped_column(Float)
    cout_lot_ht_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Brief #33 — snapshot JSON des champs visuels (laize papier, liner,
    # chute latérale, diamètre bobine, lacets, rotations). Permet de
    # rejouer SchemaImplantation côté UI sans recalculer cost_engine et
    # de ré-hydrater le store en mode édition avec un visuel fidèle.
    # Nullable pour compat lots historiques (créés avant migration).
    payload_visuel: Mapped[dict | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    devis = relationship("Devis", back_populates="lots_production")
