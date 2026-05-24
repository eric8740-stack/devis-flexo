"""Schémas Pydantic Contrôle BAT IA — Sprint 15 Lot 1.

Trois schémas exposés pour piloter le workflow contrôle BAT :

  - `ControleBatCreate` : body interne assemblé par le router POST
    `/api/flexocheck/controle-bat/` après appel à `comparer_bat_vs_tirage`
    (Lot 2). Ne sera pas exposé tel quel à l'API publique (le router
    reçoit le binaire photo + devis_id en multipart), mais sert de
    contrat pour la création d'une row ControleBat.

  - `ControleBatDetail` : retour lecture (GET liste + POST decision).

  - `DecisionFinaleIn` : body POST `/api/flexocheck/controle-bat/{id}/decision`.

Convention projet : `from_attributes=True` sur les schémas de lecture,
`extra="forbid"` sur les Create/Update pour rejeter les payloads inconnus.
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Literals partagés — alignés sur les frozenset du modèle controle_bat.py.
DecisionRecommandee = Literal["valider", "ajuster_avant_demarrage", "rejeter"]
DecisionFinale = Literal[
    "en_attente", "valide", "valide_avec_reserves", "rejete"
]
NiveauConfiance = Literal["haut", "moyen", "faible"]
ActionCorrectionSens = Literal[
    "inversion_cliche", "ajustement_rebobineuse", "confirmation_client"
]


class ControleBatCreate(BaseModel):
    """Création d'une row ControleBat (assemblée par le router Lot 3).

    `decision_finale` initiale = "en_attente" tant que l'opérateur n'a
    pas validé via POST /{id}/decision. `decideur` initial = l'utilisateur
    courant (nom_contact ou email).
    """

    model_config = ConfigDict(extra="forbid")

    devis_id: int
    bat_url: str
    bat_date_validation: datetime | None = None
    bat_valide_par: str | None = Field(None, max_length=200)
    premier_tirage_url: str
    premier_tirage_timestamp: datetime
    resultats_comparaison: dict
    score_conformite: Decimal | None = Field(None, ge=0, le=100)
    decision_recommandee: DecisionRecommandee | None = None
    ecarts_detectes: list[dict] | None = None
    nb_ecarts_majeurs: int = Field(0, ge=0)
    nb_ecarts_mineurs: int = Field(0, ge=0)
    niveau_confiance: NiveauConfiance | None = None
    decision_finale: DecisionFinale = "en_attente"
    decideur: str = Field(..., max_length=200)
    motif_decision: str | None = None
    tentative_numero: int = Field(1, ge=1)
    controle_bat_precedent_id: int | None = None
    cout_api_eur: Decimal | None = Field(None, ge=0)
    sens_sortie_detecte: str | None = Field(None, max_length=3)
    sens_enroulement_demande: str | None = Field(None, max_length=3)
    coherence_sens: bool | None = None
    action_correction_sens: ActionCorrectionSens | None = None
    position_operateur_conforme: bool | None = None


class ControleBatDetail(BaseModel):
    """Lecture d'une row ControleBat (GET liste + retour POST decision)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entreprise_id: int
    devis_id: int

    bat_url: str
    bat_date_validation: datetime | None
    bat_valide_par: str | None

    premier_tirage_url: str
    premier_tirage_timestamp: datetime

    resultats_comparaison: dict
    score_conformite: Decimal | None
    decision_recommandee: str | None
    ecarts_detectes: list[dict] | None
    nb_ecarts_majeurs: int
    nb_ecarts_mineurs: int
    niveau_confiance: str | None

    decision_finale: str
    decideur: str
    motif_decision: str | None

    tentative_numero: int
    controle_bat_precedent_id: int | None
    cout_api_eur: Decimal | None

    sens_sortie_detecte: str | None
    sens_enroulement_demande: str | None
    coherence_sens: bool | None
    action_correction_sens: str | None
    position_operateur_conforme: bool | None

    created_at: datetime


class DecisionFinaleIn(BaseModel):
    """Body POST /api/flexocheck/controle-bat/{id}/decision."""

    model_config = ConfigDict(extra="forbid")

    decision_finale: Literal["valide", "valide_avec_reserves", "rejete"]
    decideur: str = Field(..., max_length=200)
    motif_decision: str | None = None
