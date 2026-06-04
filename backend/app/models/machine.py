from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


# Rôle de la machine dans le parc (#4.3). Validé app-side (pas de CHECK SQL,
# même pattern que `ParametreMandrin.mode_par_defaut` : compat SQLite + extensible
# sans migration). "presse" = machine d'impression (génère des candidats optim) ;
# "finition" = ligne de finition / refendage / rembobinage (Daco, Rotoflex…) →
# JAMAIS candidate à l'optim presse.
TYPES_MACHINE = frozenset({"presse", "finition"})


class Machine(Base):
    """Presse flexo de l'imprimerie. Sert au calcul du temps de roulage (S3).

    B1 (convergence option B, 2026-05-30) : champs optim ajoutes
    (`laize_utile_mm`, `nb_postes_decoupe`, `options`) + renommage
    `nb_couleurs` -> `nb_groupes_couleurs` pour converger avec
    `MachineImprimerie` (deprecie depuis B3a). `Machine` est la source
    unique du parc machines.

    B3b (2026-06-01) : DROP COLUMN `vitesse_pratique_m_min` (cleanup post
    B3a -- le moteur derive `vitesse_moyenne_m_h / 60` a la volee dans
    `optimisation_loader.charger_machines_actives`, plus aucune lecture
    de la colonne).

    Les champs SACRES (`laize_max_mm`, `vitesse_moyenne_m_h`,
    `duree_calage_h`) restent INTOUCHES -- ils sont lus par cost_engine
    (cylindre_matcher / poste_5_roulage / poste_7_mo) et garantissent
    V1a 1 449,09 EUR EXACT.
    """

    __tablename__ = "machine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Sprint 12 multi-tenant — scope par entreprise (cf. client.py)
    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nom: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    largeur_max_mm: Mapped[int | None] = mapped_column(Integer)
    vitesse_max_m_min: Mapped[int | None] = mapped_column(Integer)
    # B1 : renomme depuis `nb_couleurs` (migration z0p4n6r8s1t3). Aligne sur
    # `MachineImprimerie.nb_groupes_couleurs` (Sprint 13.B). Donnees preservees.
    nb_groupes_couleurs: Mapped[int | None] = mapped_column(Integer)
    cout_horaire_eur: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Sprint 7 Lot 7a — laize machine (largeur max imprimable physique de la
    # presse, mm). Sert au matching cylindres magnétiques (contrainte largeur
    # plaque ≤ laize_max - 2 × MARGE_SECURITE_LAIZE_MM). Sémantique alignée
    # sur largeur_max_mm pour les machines actuelles (à dédupliquer Sprint 8).
    laize_max_mm: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    # Paramètres calcul S3 — vitesse réaliste de production (vs vitesse_max
    # qui reste un argument catalogue) et durée de mise au point machine.
    vitesse_moyenne_m_h: Mapped[int | None] = mapped_column(Integer)
    duree_calage_h: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))

    # B1 (convergence option B, migration z0p4n6r8s1t3) — champs optim absorbes
    # depuis MachineImprimerie. Consommes par le loader optimisation_loader.
    # Tenant demo seede par data migration (laize_utile := laize_max).
    # Nouveaux tenants : nullable -> a completer via l'UI B2.
    # B3b (migration a1b2c3d4e5f6) : `vitesse_pratique_m_min` retire --
    # le moteur derive `vitesse_moyenne_m_h / 60` a la volee.
    laize_utile_mm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    nb_postes_decoupe: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    options: Mapped[list[str] | None] = mapped_column(
        JSON, default=list, server_default="[]"
    )

    # Sprint 9 v2 : refactor `statut` String → `actif` Boolean.
    # Mapping migration : 'actif'/'maintenance' → True, 'inactif' → False
    # (perte info "maintenance" assumée par Eric brief 4.3).
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # #4.3 — rôle de la machine. Défaut "presse" (server_default) : toute
    # machine existante reste une presse. Les finitions (Daco / Rotoflex) sont
    # re-typées par data migration. Le loader d'optim ne charge que les presses.
    type_machine: Mapped[str] = mapped_column(
        String(20), nullable=False, default="presse", server_default="presse"
    )

    commentaire: Mapped[str | None] = mapped_column(Text)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
