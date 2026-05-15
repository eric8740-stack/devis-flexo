"""Schémas Pydantic — optimisation Sprint 13 Lot S13.D.7b.

POST /api/optimisation/calculer : reçoit le contexte devis + sélection
matière/options, hydrate depuis la BDD (cylindres + machines + barèmes
du tenant) puis appelle optimiser_pose(). Renvoie top 3 + metadata.

extra='forbid' partout pour rejeter les champs accessoires.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class OptimisationFormat(BaseModel):
    """Format d'étiquette demandé."""

    model_config = ConfigDict(extra="forbid")

    hauteur_mm: float = Field(..., gt=0, le=2000)
    largeur_mm: float = Field(..., gt=0, le=2000)
    rayon_angles_mm: float = Field(2.0, ge=0, le=999)
    forme_courbe: bool = False


class OptimisationContrainteClient(BaseModel):
    """Contraintes machine de pose client (optionnel)."""

    model_config = ConfigDict(extra="forbid")

    intervalle_dev_min_mm: float = Field(0.0, ge=0, le=20)


class OptimisationCalculerRequest(BaseModel):
    """Body de POST /api/optimisation/calculer.

    Les cylindres + machines + barèmes sont hydratés côté serveur depuis
    le tenant (pas d'ID à passer). Seules les sélections du commercial
    transitent : format, options, contraintes.
    """

    model_config = ConfigDict(extra="forbid")

    format: OptimisationFormat
    intervalle_dev_min_mm: float = Field(
        2.0, ge=0, le=20, description="Plancher imprimeur (typique 2 mm)"
    )
    nb_couleurs_impression: int = Field(
        ..., ge=0, le=16, description="CMJN + Pantone + spot"
    )
    quantite: int = Field(..., gt=0, le=100_000_000)
    matiere_est_transparente: bool = False
    options_codes: list[str] = Field(
        default_factory=list,
        description="Codes options du tenant (table option_fabrication)",
    )
    contrainte_client: OptimisationContrainteClient = Field(
        default_factory=OptimisationContrainteClient
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OptimisationConfigOut(BaseModel):
    """Une configuration candidate du top N."""

    model_config = ConfigDict(extra="forbid")

    cylindre_id: int
    machine_id: int
    nb_poses_dev: int
    nb_poses_laize: int
    nb_poses_total: int
    intervalle_dev_reel_mm: float
    intervalle_laize_reel_mm: float
    largeur_plaque_mm: float
    z_mini_effet_banane: float
    qualite_echenillage: str
    consolidation_atteinte: bool
    intervalle_laize_souhaitable_mm: float | None = None
    disposition_poses: str
    coef_vitesse_echenillage: float
    coef_gache_echenillage: float
    coef_confort_rayon: float
    coef_quinconce: float
    coef_consolidation: float
    coef_vitesse_options: float
    coef_gache_options: float
    coef_vitesse_final: float
    coef_gache_final: float
    score: float


class OptimisationCalculerResponse(BaseModel):
    """Top N (≤ 3) + métadonnées explicatives."""

    model_config = ConfigDict(extra="forbid")

    configurations: list[OptimisationConfigOut]
    nb_candidats: int
    message_filtrage: str | None = None
    intervalle_dev_min_applique_mm: float
    message_contrainte_client: str | None = None
    debug: dict[str, Any] | None = None
