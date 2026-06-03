"""Modèle ParametreMandrin — Sprint 16 Lot A (Module Rebobinage).

Paramètres globaux par entreprise pour la gestion des mandrins :
disponibilité d'une scie interne (pour la découpe interne), délais
fournisseur, stock de sécurité par modèle, mode par défaut
(auto / pre_coupe / decoupe_interne).

Cardinalité : 1 row par entreprise (UNIQUE entreprise_id). Pattern
similaire à un singleton de configuration tenant.

Convention naming : table au singulier `parametre_mandrin` (cohérent
avec `machine_rebobineuse`, `cylindre_magnetique`, etc.). Le brief
Sprint 16 mentionne "Extension parametres_mandrins" — la table n'existe
pas dans le projet, on la crée ici.

`stock_securite_par_modele` est un JSON dict mappant diamètre mandrin
(en mm, en str pour clé JSON) à quantité stock minimum, ex :
  {"25": 200, "38": 150, "76": 80, "152": 30}

`mode_par_defaut` pilote l'arbitrage du Lot B (moteur rebobinage) :
- "auto"          : le moteur choisit pré-coupé vs découpe interne
                    selon coût optimal calculé.
- "pre_coupe"     : force l'achat de mandrins pré-coupés.
- "decoupe_interne": force la découpe interne (suppose scie_disponible).
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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


# Modes d'arbitrage du moteur de rebobinage (Lot B).
MODES_PAR_DEFAUT = frozenset({"auto", "pre_coupe", "decoupe_interne"})


class ParametreMandrin(Base):
    """Paramètres mandrins globaux d'une entreprise (singleton tenant)."""

    __tablename__ = "parametre_mandrin"
    __table_args__ = (
        UniqueConstraint("entreprise_id", name="uq_parametre_mandrin_entreprise"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scie disponible en interne — prérequis pour la découpe interne
    # (Lot B). Si False, le mode "decoupe_interne" doit être refusé par
    # le moteur (= rétrograde vers "pre_coupe").
    scie_disponible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Délai standard de livraison des mandrins pré-coupés par le
    # fournisseur (en jours ouvrés). Nullable si l'entreprise n'a pas
    # de fournisseur de pré-coupé référencé.
    delai_livraison_fournisseur_jours: Mapped[int | None] = mapped_column(Integer)

    # Stock de sécurité minimum par diamètre mandrin (clé JSON = str(mm)).
    # ex: {"25": 200, "38": 150, "76": 80, "152": 30}
    stock_securite_par_modele: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Épaisseur de paroi du mandrin (mm). Destiné au calcul du Ø rouleau
    # (bug #6 chaîne Format→Outil→Matière→Bobinage, étape 6.2 — NON câblé
    # ici). NULLABLE : NULL = inconnu (aucune valeur en dur ; renseigné
    # ensuite par l'imprimeur). Étape 6.1 : on crée seulement le champ.
    epaisseur_paroi_mm: Mapped[int | None] = mapped_column(Integer)

    # Mode d'arbitrage par défaut — pilote le moteur Lot B.
    # Validé app-side via MODES_PAR_DEFAUT (pas de CHECK SQL pour rester
    # compat SQLite + extensibilité V2 sans migration).
    mode_par_defaut: Mapped[str] = mapped_column(
        String(20), nullable=False, default="auto", server_default="auto"
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    date_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
