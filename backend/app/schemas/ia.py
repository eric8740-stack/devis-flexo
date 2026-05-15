"""Schémas Pydantic — IA Sprint 13 Lot S13.E.3.

POST /api/ia/analyser-photo : reçoit une image base64 + mime, renvoie
le payload Claude structuré (10 champs CHAMPS_REQUIS du service S13.E.1).

extra='forbid' partout pour rejeter les champs accessoires.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


MIME_TYPES_AUTORISES = ("image/jpeg", "image/png", "image/webp", "image/gif")


class AnalysePhotoRequest(BaseModel):
    """Body POST /api/ia/analyser-photo.

    L'image est envoyée en base64 standard (avec ou sans préfixe
    `data:image/jpeg;base64,...` — on tolère les deux). En MVP on ne
    stocke pas l'image sur Vercel Blob, le router décode et envoie
    directement à Claude.
    """

    model_config = ConfigDict(extra="forbid")

    image_base64: str = Field(
        ...,
        min_length=1,
        max_length=15_000_000,  # ~10 Mo en base64
        description="Contenu image en base64 (avec ou sans prefix data:)",
    )
    mime_type: str = Field(
        ...,
        description=f"Un de : {', '.join(MIME_TYPES_AUTORISES)}",
    )
    devis_id: int | None = Field(
        default=None,
        description="Devis a rattacher (optionnel - analyse exploratoire OK)",
    )
    image_filename: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Nom de fichier d'origine cote client (ex 'etiquette-bio.jpg')."
            " Stocke pour affichage UI dans l'historique."
        ),
    )


class AnalysePhotoResponse(BaseModel):
    """Réponse : id de la row persistée + payload Claude intégral."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="ID de la row analyse_photo_etiquette")
    resultats_ia: dict[str, Any] = Field(
        ..., description="JSON complet renvoye par Claude (10 champs)"
    )
    niveau_confiance: str
    nombre_couleurs_distinctes: int | None
    model_utilise: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Historique des analyses photo (feat-historique-analyses)
# ---------------------------------------------------------------------------


class AnalysePhotoListItem(BaseModel):
    """Une row dans la liste paginée /api/ia/analyses (vue resumé).

    Pas de resultats_ia (lourd, 5-10 KB chacun) — uniquement les
    metadonnees affichees dans la liste. Pour le detail complet,
    GET /api/ia/analyses/{id}.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    image_filename: str | None
    image_key: str | None
    photo_mime_type: str | None
    image_size_bytes: int | None
    niveau_confiance: str | None
    nombre_couleurs_distinctes: int | None
    erreur: str | None
    created_at: str


class AnalysePhotoListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AnalysePhotoListItem]
    page: int
    limit: int
    total: int


class AnalysePhotoDetail(BaseModel):
    """Vue détaillée /api/ia/analyses/{id} : tous les champs + payload IA."""

    model_config = ConfigDict(extra="forbid")

    id: int
    image_filename: str | None
    image_key: str | None
    photo_mime_type: str | None
    image_size_bytes: int | None
    resultats_ia: dict[str, Any]
    niveau_confiance: str | None
    nombre_couleurs_distinctes: int | None
    model_utilise: str | None
    erreur: str | None
    devis_id: int | None
    created_at: str
