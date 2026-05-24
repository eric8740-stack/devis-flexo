"""Modèle ControleBat — Sprint 15 Lot 1 (FlexoCheck).

Trace un contrôle BAT IA (Bon À Tirer comparé au 1er tirage en sortie de
presse). Une row par tentative ; le chaînage des re-tirages se fait via
`controle_bat_precedent_id` (self-FK SET NULL pour préserver l'historique
si une row parente est purgée).

Multi-tenant : `entreprise_id` NOT NULL FK CASCADE — la suppression d'une
entreprise efface ses contrôles. `devis_id` NOT NULL FK CASCADE — un
contrôle est toujours rattaché à un devis (la production contrôlée).

Conventions projet appliquées vs CdC :
  - UUID → Integer autoincrement (cohérent avec photo_production,
    rapport_qualite_production, lot_production)
  - company_id → entreprise_id, devis_specs_id → devis_id
  - JSONB → JSONB().with_variant(JSON(), "sqlite") (pattern Brief #33)
  - Table au singulier `controle_bat` (cohérent avec photo_production)

Le sens de sortie détecté (`sens_sortie_detecte`) est stocké en VARCHAR(3)
au format SE1..SE8 — la convention SE1-SE8 est verrouillée le 18/05/2026,
les rotations sont mappées via `app/services/rotation_se.py` (sacred,
lecture seule).
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


# Valeurs autorisées pour decision_recommandee et decision_finale —
# validées côté Pydantic, pas en CHECK SQL pour rester compatible SQLite
# et garder l'extensibilité V2 sans migration.
DECISIONS_RECOMMANDEES = frozenset(
    {"valider", "ajuster_avant_demarrage", "rejeter"}
)
DECISIONS_FINALES = frozenset(
    {"en_attente", "valide", "valide_avec_reserves", "rejete"}
)
NIVEAUX_CONFIANCE = frozenset({"haut", "moyen", "faible"})
ACTIONS_CORRECTION_SENS = frozenset(
    {"inversion_cliche", "ajustement_rebobineuse", "confirmation_client"}
)


class ControleBat(Base):
    """Contrôle BAT IA d'un 1er tirage vs BAT validé client.

    Une tentative = une row. Le re-tirage crée une nouvelle row qui
    pointe vers la précédente via `controle_bat_precedent_id` et
    incrémente `tentative_numero`. Le service Lot 3 force la cohérence
    `entreprise_id`/`devis_id` entre les maillons de la chaîne.
    """

    __tablename__ = "controle_bat"
    __table_args__ = (
        Index("ix_controle_bat_entreprise", "entreprise_id"),
        Index("ix_controle_bat_devis", "devis_id"),
        Index("ix_controle_bat_precedent", "controle_bat_precedent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entreprise_id: Mapped[int] = mapped_column(
        ForeignKey("entreprise.id", ondelete="CASCADE"), nullable=False
    )
    devis_id: Mapped[int] = mapped_column(
        ForeignKey("devis.id", ondelete="CASCADE"), nullable=False
    )

    # --- BAT de référence (Vercel Blob) ------------------------------------
    bat_url: Mapped[str] = mapped_column(Text, nullable=False)
    bat_date_validation: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    bat_valide_par: Mapped[str | None] = mapped_column(String(200))

    # --- Photo 1er tirage (Vercel Blob) ------------------------------------
    premier_tirage_url: Mapped[str] = mapped_column(Text, nullable=False)
    premier_tirage_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # --- Résultat IA Claude API --------------------------------------------
    # Réponse JSON complète (cf. prompt controle_bat.txt Lot 2).
    resultats_comparaison: Mapped[Any] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    score_conformite: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # valider | ajuster_avant_demarrage | rejeter
    decision_recommandee: Mapped[str | None] = mapped_column(String(30))
    ecarts_detectes: Mapped[Any | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )
    nb_ecarts_majeurs: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    nb_ecarts_mineurs: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # haut | moyen | faible
    niveau_confiance: Mapped[str | None] = mapped_column(String(20))

    # --- Décision opérateur / chef atelier ---------------------------------
    # en_attente (init) | valide | valide_avec_reserves | rejete
    decision_finale: Mapped[str] = mapped_column(String(30), nullable=False)
    decideur: Mapped[str] = mapped_column(String(200), nullable=False)
    motif_decision: Mapped[str | None] = mapped_column(Text)

    # --- Chaînage re-tirage ------------------------------------------------
    tentative_numero: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    controle_bat_precedent_id: Mapped[int | None] = mapped_column(
        ForeignKey("controle_bat.id", ondelete="SET NULL")
    )

    # --- Coût API IA --------------------------------------------------------
    cout_api_eur: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))

    # --- Sens sortie (Lot 4) -----------------------------------------------
    # SE1..SE8 — format VARCHAR(3) volontaire pour rester lisible humain
    # plutôt qu'un int 1..8 ; le mapping libellé/rotation reste dans
    # rotation_se.py (sacred lecture seule).
    sens_sortie_detecte: Mapped[str | None] = mapped_column(String(3))
    sens_enroulement_demande: Mapped[str | None] = mapped_column(String(3))
    coherence_sens: Mapped[bool | None] = mapped_column(Boolean)
    # inversion_cliche | ajustement_rebobineuse | confirmation_client
    action_correction_sens: Mapped[str | None] = mapped_column(String(50))
    position_operateur_conforme: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
