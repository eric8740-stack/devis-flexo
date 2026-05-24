"""Wrapper bas niveau Anthropic SDK Sprint 13 Lot S13.E.

Réutilisable pour tous les modules IA futurs (analyse photo étiquette
S13.E, contrôle BAT Sprint 14, photos palettes Sprint 15, etc.).

Décisions :
  - Lazy init du client : on n'instancie qu'à l'appel (évite de crasher
    au boot si ANTHROPIC_API_KEY n'est pas définie en dev).
  - Modèle paramétrable par appel + default sur claude-sonnet-4-6
    (compromis rapidité / qualité pour multimodal). On peut basculer
    sur opus pour les cas qui requièrent plus de finesse.
  - Erreur explicite si ANTHROPIC_API_KEY absente — pas d'appel silencieux
    qui timeout après 30s.
  - Helper `analyser_image(prompt, image_bytes, mime_type)` qui encapsule
    le format messages multimodal pour ne pas dupliquer ce boilerplate
    dans chaque service.

Le SDK Anthropic est synchrone côté Python : on garde cette API simple
(les appels prennent 2-10s typiquement, on fait pas d'async dans FastAPI
pour ça — l'event loop n'est pas bloqué grâce à la threadpool FastAPI).
"""
from __future__ import annotations

import base64
import os
from typing import Any


class IAClientError(Exception):
    """Erreur fonctionnelle remontée aux services (clé absente,
    réponse Claude inutilisable, etc.)."""


# Modèle par défaut — Sonnet 4.6 : multimodal, rapide, bonne qualité.
# Pour analyse fine on peut basculer sur opus, pour batch on peut
# basculer sur haiku.
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1024


def _get_anthropic_client():
    """Lazy import + init pour ne pas crasher au boot si clé absente."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise IAClientError(
            "ANTHROPIC_API_KEY non définie. Configurez-la dans "
            "votre fichier .env (dev) ou les variables d'environnement "
            "Railway (prod)."
        )
    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError as exc:
        raise IAClientError(
            "Le SDK anthropic n'est pas installé. "
            "Lancez : pip install -r requirements.txt"
        ) from exc
    return anthropic.Anthropic(api_key=api_key)


def analyser_image(
    prompt_text: str,
    image_bytes: bytes,
    mime_type: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Envoie une image + un prompt à Claude API et renvoie le texte brut.

    Args:
      prompt_text : le prompt en clair (typiquement chargé depuis
        prompts/*.txt par le service appelant).
      image_bytes : contenu binaire de l'image.
      mime_type : "image/jpeg" | "image/png" | "image/webp" | "image/gif".
      model : ID modèle (default claude-sonnet-4-6).
      max_tokens : limite de tokens en sortie (1024 suffit pour notre JSON).

    Returns:
      Le texte de la réponse Claude (à parser par le service appelant
      si du JSON structuré est attendu).

    Raises:
      IAClientError : clé absente, SDK absent, ou réponse vide.
    """
    if not image_bytes:
        raise IAClientError("image_bytes vide")
    if mime_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }:
        raise IAClientError(
            f"mime_type non supporté : {mime_type}. "
            f"Attendu : image/jpeg | image/png | image/webp | image/gif."
        )

    client = _get_anthropic_client()
    image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    )

    # La réponse Claude est une liste de blocs (text + tool_use éventuels).
    # Pour notre usage simple, on concatène les blocs text.
    texte_parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            texte_parts.append(block.text)
    texte = "".join(texte_parts).strip()
    if not texte:
        raise IAClientError(
            "Claude a renvoyé une réponse vide (pas de bloc text)."
        )
    return texte


def analyser_images(
    prompt_text: str,
    images: list[tuple[bytes, str]],
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> tuple[str, dict[str, int]]:
    """Variante multi-images de `analyser_image` (Sprint 15 Lot 2).

    Envoie N images + un prompt à Claude API. Utilisée par le service
    Contrôle BAT IA qui compare BAT vs 1er tirage (2 images). Reste
    générique pour d'éventuels usages futurs (palette + BAT…).

    Args:
      prompt_text : prompt en clair.
      images : liste de tuples `(image_bytes, mime_type)` dans l'ordre
        où Claude doit les voir. Au moins 1 image.
      model : ID modèle (default claude-sonnet-4-6).
      max_tokens : limite tokens sortie.

    Returns:
      Tuple `(texte_reponse, usage_dict)` où `usage_dict` contient
      `{"input_tokens": int, "output_tokens": int}` extraits de la
      réponse Anthropic — sert au service appelant à calculer un
      coût €/contrôle.

    Raises:
      IAClientError : clé absente, SDK absent, image vide / mime invalide,
      liste vide, ou réponse Claude vide.
    """
    if not images:
        raise IAClientError("Aucune image fournie")
    for image_bytes, mime_type in images:
        if not image_bytes:
            raise IAClientError("image_bytes vide")
        if mime_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
        }:
            raise IAClientError(
                f"mime_type non supporté : {mime_type}. "
                f"Attendu : image/jpeg | image/png | image/webp | image/gif."
            )

    client = _get_anthropic_client()

    content: list[dict[str, Any]] = []
    for image_bytes, mime_type in images:
        image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": image_b64,
                },
            }
        )
    content.append({"type": "text", "text": prompt_text})

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )

    texte_parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            texte_parts.append(block.text)
    texte = "".join(texte_parts).strip()
    if not texte:
        raise IAClientError(
            "Claude a renvoyé une réponse vide (pas de bloc text)."
        )

    # `message.usage` existe sur les SDK Anthropic récents. On reste
    # défensif si jamais un mock le renvoie absent.
    usage = getattr(message, "usage", None)
    usage_dict = {
        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
    }
    return texte, usage_dict


# Helpers techniques pour les services
def lire_prompt(nom_fichier: str) -> str:
    """Charge un prompt depuis app/services/ia/prompts/<nom_fichier>.

    Utilisé par les services pour découpler les prompts (texte versionné
    en repo) du code Python. Si le fichier est introuvable, on lève une
    IAClientError plutôt que FileNotFoundError pour homogénéiser les
    erreurs vis-à-vis du router.
    """
    from pathlib import Path

    chemin = Path(__file__).parent / "prompts" / nom_fichier
    if not chemin.exists():
        raise IAClientError(f"Prompt introuvable : {chemin}")
    return chemin.read_text(encoding="utf-8")


def parse_json_strict(texte_brut: str) -> dict[str, Any]:
    """Parse un JSON renvoyé par Claude en mode strict.

    Tente d'abord un json.loads direct. Si Claude a malgré tout enrobé
    le JSON dans ```json ... ``` (malgré les instructions du prompt), on
    nettoie. Si le JSON est invalide → IAClientError avec le texte brut
    pour debug.
    """
    import json
    import re

    texte = texte_brut.strip()
    # Cas où Claude a quand même ajouté un fence
    if texte.startswith("```"):
        # Enlève ```json ... ``` ou ``` ... ```
        match = re.match(r"```(?:json)?\s*([\s\S]*?)\s*```\s*$", texte)
        if match:
            texte = match.group(1).strip()

    try:
        return json.loads(texte)
    except json.JSONDecodeError as exc:
        raise IAClientError(
            f"Réponse Claude n'est pas un JSON valide : {exc}. "
            f"Texte brut : {texte_brut[:500]}..."
        ) from exc
