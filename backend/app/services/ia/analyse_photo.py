"""Service POC analyse photo étiquette Sprint 13 Lot S13.E.

Charge le prompt depuis prompts/analyse_photo.txt, envoie l'image à
Claude API multimodal, parse le JSON strict attendu.

C'est une estimation préliminaire pour cadrer rapidement la demande
client (CdC § 1842). Le BAT (Bon à Tirer) reste obligatoire pour valider
les couleurs exactes — l'IA n'est PAS une analyse colorimétrique
calibrée.

Champs attendus dans le JSON Claude (cf. prompts/analyse_photo.txt) :
  - couleurs_detectees     : liste de {rgb, pantone_proche, surface_pct}
  - nombre_couleurs_distinctes
  - couleurs_min_technique : stations couleur minimum requises
  - couleurs_max_technique : avec toutes les techniques visibles
  - techniques_impression_estimees : ["CMJN", "Pantone spot", ...]
  - matiere_estimee        : {type, couleur, finition_apparente}
  - finitions_visibles     : ["dorure_chaud", "vernis_selectif", ...]
  - presence_blanc_opaque  : bool
  - niveau_confiance       : "haut" | "moyen" | "faible"
  - limites_analyse        : ["éclairage défavorable", ...]
"""
from __future__ import annotations

from typing import Any

from app.services.ia.client import (
    IAClientError,
    analyser_image,
    lire_prompt,
    parse_json_strict,
)
from app.services.ia.support_reserve import appliquer_support_reserve


# Champs obligatoires dans la réponse Claude — si l'un manque on lève une
# erreur explicite plutôt que de retourner un payload incomplet au front.
CHAMPS_REQUIS = (
    "couleurs_detectees",
    "nombre_couleurs_distinctes",
    "couleurs_min_technique",
    "couleurs_max_technique",
    "techniques_impression_estimees",
    "matiere_estimee",
    "finitions_visibles",
    "presence_blanc_opaque",
    "niveau_confiance",
    "limites_analyse",
)

NIVEAUX_CONFIANCE_AUTORISES = frozenset({"haut", "moyen", "faible"})


def analyser_photo_etiquette(
    image_bytes: bytes, mime_type: str
) -> dict[str, Any]:
    """Analyse une photo d'étiquette et renvoie l'estimation structurée.

    Pipeline :
      1. Charge le prompt depuis prompts/analyse_photo.txt
      2. Appelle Claude API multimodal via analyser_image()
      3. Parse le JSON strict
      4. Valide la présence des champs requis + le niveau_confiance

    Lève IAClientError en cas d'image vide, mime type invalide, réponse
    Claude inexploitable, ou champ requis manquant.
    """
    prompt = lire_prompt("analyse_photo.txt")
    texte = analyser_image(prompt, image_bytes, mime_type)
    payload = parse_json_strict(texte)

    manquants = [c for c in CHAMPS_REQUIS if c not in payload]
    if manquants:
        raise IAClientError(
            f"Réponse Claude incomplète, champs manquants : {manquants}. "
            f"Réponse partielle : {list(payload.keys())}"
        )

    niveau = payload.get("niveau_confiance")
    if niveau not in NIVEAUX_CONFIANCE_AUTORISES:
        raise IAClientError(
            f"niveau_confiance invalide : {niveau!r}. "
            f"Attendu : {sorted(NIVEAUX_CONFIANCE_AUTORISES)}"
        )

    # Fix analyseur photo : flag support_reserve par couleur + recalcul des
    # compteurs de stations en excluant les réserves papier. Évite la
    # surfacturation systématique d'une station sur les défonces blanches
    # imprimées sur papier blanc (cas typique des étiquettes alimentaires).
    appliquer_support_reserve(payload)

    return payload
