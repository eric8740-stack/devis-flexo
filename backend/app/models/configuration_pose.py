"""Modèle ConfigurationPose — Sprint 13 Lot S13.B.

Stocke les **résultats du moteur d'optimisation** (Lot S13.D). Pour un
devis donné, le moteur produit UP TO 3 configurations de pose candidates
(cf. règle "pas de triche" : on peut en retourner moins, mais jamais
plus de 3). Chaque candidate matérialise un couple (cylindre × machine)
avec ses poses, ses coefs, ses coûts et son score.

L'utilisateur commercial sélectionne ensuite la configuration retenue
(`est_retenue=True`) ou la surcharge manuellement (Règle 7 du moteur —
souveraineté commerciale). La surcharge est tracée intégralement
(forcage_manuel + champs_surcharges JSON + motif_forcage + snapshot
valeurs_recommandees_initiales) pour audit ultérieur.

Multi-tenant : entreprise_id NOT NULL FK CASCADE. devis_id optionnel
car le moteur peut être appelé en simulation sans persister un devis.

NB : on référence la table `devis` existante (Sprint 4), pas une
nouvelle table `devis_specs`. Le CdC mentionne `devis_specs(id)` mais
notre projet a déjà `devis` qui contient les payload_input/output.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConfigurationPose(Base):
    __tablename__ = "configuration_pose"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # devis_id optionnel : le moteur peut être appelé en simulation sans
    # avoir encore créé de devis persistant. À l'enregistrement définitif,
    # on rattache via UPDATE.
    devis_id: Mapped[int | None] = mapped_column(
        ForeignKey("devis.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Cylindre et machine choisis pour cette config — couple cœur du moteur.
    cylindre_id: Mapped[int] = mapped_column(
        ForeignKey("cylindre_magnetique.id", ondelete="RESTRICT"),
        nullable=False,
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machine_imprimerie.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Pose résultante
    nb_poses_dev: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_poses_laize: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_poses_total: Mapped[int] = mapped_column(Integer, nullable=False)
    intervalle_dev_reel_mm: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    intervalle_laize_reel_mm: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    intervalle_laize_souhaitable_mm: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2)
    )
    consolidation_atteinte: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Règle 5 — Confort de roulage
    rayon_angles_mm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    forme_courbe: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    disposition_poses: Mapped[str] = mapped_column(
        String(20), nullable=False, default="alignee"
    )
    coef_confort_rayon: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )
    coef_quinconce: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )

    # Règle 2 — Effet banane (traçabilité de la décision)
    largeur_plaque_mm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    z_mini_effet_banane: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    # Règle 3 — Qualité d'échenillage
    qualite_echenillage: Mapped[str | None] = mapped_column(String(20))
    coef_vitesse: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )
    coef_gache: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )
    couleur_alerte: Mapped[str | None] = mapped_column(String(10))

    # Production & coûts
    taux_utilisation_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    gache_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    temps_production_h: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    cout_machine_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    cout_matiere_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    cout_total_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    surcout_vs_optimal_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    # optimale | alternative | manuelle | degradee_subie
    type_config: Mapped[str | None] = mapped_column(String(20))
    est_retenue: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Règle 7 — Souveraineté commerciale (traçabilité surcharge)
    forcage_manuel: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    valeurs_recommandees_initiales: Mapped[Any | None] = mapped_column(JSON)
    champs_surcharges: Mapped[list[str] | None] = mapped_column(JSON)
    motif_forcage: Mapped[str | None] = mapped_column(Text)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
