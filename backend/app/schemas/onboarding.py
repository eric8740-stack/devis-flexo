"""Schémas Pydantic — onboarding Sprint 13 Lot S13.C.

GET /api/onboarding/catalogue-defaults  → expose le catalogue figé
POST /api/onboarding/initialiser-catalogues → applique la sélection

`extra="forbid"` partout pour rejeter les champs accessoires.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# GET /api/onboarding/catalogue-defaults — réponse
# ---------------------------------------------------------------------------


class OnboardingCatalogueDefaults(BaseModel):
    """Le catalogue par défaut tel qu'il est affiché à l'utilisateur dans le
    tunnel d'onboarding (4 écrans).

    On laisse les dicts ouverts (`list[dict[str, Any]]`) car la structure
    interne change entre catalogues (matière vs option vs barème) — le
    typage strict côté UI est fait dans le frontend Next.js.
    """

    model_config = ConfigDict(extra="forbid")

    cylindres_developpes_mm: list[float] = Field(
        ..., description="19 développés standard flexo (72 à 144 mm)"
    )
    machines: list[dict[str, Any]] = Field(
        ..., description="3 machines types pré-configurées"
    )
    matieres: list[dict[str, Any]] = Field(
        ..., description="30 matières du marché"
    )
    options: list[dict[str, Any]] = Field(
        ..., description="20 options de fabrication"
    )
    baremes: list[dict[str, Any]] = Field(
        ..., description="4 barèmes ICE (échenillage, banane, confort, compensation)"
    )


# ---------------------------------------------------------------------------
# POST /api/onboarding/initialiser-catalogues — request + response
# ---------------------------------------------------------------------------


class OnboardingInitRequest(BaseModel):
    """Sélection de l'utilisateur dans le tunnel d'onboarding.

    Les barèmes sont TOUJOURS chargés (pas d'opt-out), donc absents
    de ce request : c'est l'engagement minimal d'utiliser FlexoCompare.
    """

    model_config = ConfigDict(extra="forbid")

    cylindres_developpes_mm: list[float] = Field(
        default_factory=list,
        description="Développés cochés par l'utilisateur (subset des 19)",
    )
    machines_codes: list[str] = Field(
        default_factory=list,
        description="Codes machines cochés (subset des 3)",
    )
    matieres_codes: list[str] = Field(
        default_factory=list,
        description="Codes matières cochés (subset des 30)",
    )
    options_codes: list[str] = Field(
        default_factory=list,
        description="Codes options cochés (subset des 20)",
    )


class OnboardingInitResponse(BaseModel):
    """Compteurs de rows créées par catalogue + total."""

    model_config = ConfigDict(extra="forbid")

    cylindres: int
    machines: int
    matieres: int
    options: int
    baremes: int
    total: int
