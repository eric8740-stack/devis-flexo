"""Tests du service IA analyse photo Sprint 13 S13.E.1.

Aucun appel réel à l'API Claude — on mock le SDK Anthropic via
monkeypatch pour rester rapide + offline + reproductible en CI.

Couvre :
  - Wrapper client : erreurs si ANTHROPIC_API_KEY absente / mime invalide / image vide
  - parse_json_strict : JSON propre, JSON fence ```json```, JSON invalide
  - lire_prompt : prompt présent / introuvable
  - analyser_photo_etiquette : happy path, champ manquant, niveau_confiance invalide
"""
import json
import os
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services.ia import client as ia_client
from app.services.ia.analyse_photo import analyser_photo_etiquette
from app.services.ia.client import (
    IAClientError,
    analyser_image,
    lire_prompt,
    parse_json_strict,
)


# ---------------------------------------------------------------------------
# Helpers — mock du SDK Anthropic
# ---------------------------------------------------------------------------


def _mock_anthropic_response(texte: str):
    """Construit une réponse fake conforme à anthropic.Anthropic.messages.create."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = texte
    response = MagicMock()
    response.content = [text_block]
    return response


def _install_mock_client(monkeypatch, texte_retour: str):
    """Remplace _get_anthropic_client par un mock qui retourne `texte_retour`."""
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        texte_retour
    )
    monkeypatch.setattr(
        ia_client, "_get_anthropic_client", lambda: fake_client
    )
    return fake_client


# ---------------------------------------------------------------------------
# parse_json_strict
# ---------------------------------------------------------------------------


def test_parse_json_strict_propre():
    payload = parse_json_strict('{"foo": "bar"}')
    assert payload == {"foo": "bar"}


def test_parse_json_strict_avec_fence_markdown():
    """Claude ajoute parfois ```json ... ``` malgré l'instruction du prompt.
    On nettoie."""
    texte = "```json\n{\"foo\": 42}\n```"
    payload = parse_json_strict(texte)
    assert payload == {"foo": 42}


def test_parse_json_strict_avec_fence_simple():
    texte = "```\n{\"x\": true}\n```"
    payload = parse_json_strict(texte)
    assert payload == {"x": True}


def test_parse_json_strict_json_invalide_leve_iaclienterror():
    with pytest.raises(IAClientError) as exc_info:
        parse_json_strict("ceci n'est pas du JSON")
    assert "n'est pas un JSON valide" in str(exc_info.value)


# ---------------------------------------------------------------------------
# lire_prompt
# ---------------------------------------------------------------------------


def test_lire_prompt_analyse_photo_existe():
    """Le prompt S13.E doit être présent dans le repo."""
    contenu = lire_prompt("analyse_photo.txt")
    assert len(contenu) > 100
    # Sanity : on retrouve les marqueurs du prompt CdC
    assert "JSON" in contenu
    assert "couleurs_detectees" in contenu
    assert "niveau_confiance" in contenu


def test_lire_prompt_introuvable_leve_iaclienterror():
    with pytest.raises(IAClientError) as exc_info:
        lire_prompt("introuvable.txt")
    assert "introuvable" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# analyser_image — validations input + happy path mocké
# ---------------------------------------------------------------------------


def test_analyser_image_leve_si_api_key_absente(monkeypatch):
    """Sans ANTHROPIC_API_KEY → IAClientError explicite (pas de fetch
    réseau qui timeout en silence)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(IAClientError) as exc_info:
        analyser_image("Hello", b"fake-image-bytes", "image/jpeg")
    assert "ANTHROPIC_API_KEY" in str(exc_info.value)


def test_analyser_image_leve_si_mime_type_inconnu(monkeypatch):
    # On set la clé pour passer la 1ere vérif, mais notre mime invalide
    # déclenche avant l'appel SDK.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    with pytest.raises(IAClientError) as exc_info:
        analyser_image("Hello", b"fake", "image/svg+xml")
    assert "mime_type" in str(exc_info.value).lower()


def test_analyser_image_leve_si_bytes_vides(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    with pytest.raises(IAClientError):
        analyser_image("Hello", b"", "image/jpeg")


def test_analyser_image_happy_path_appelle_sdk(monkeypatch):
    """Appel mocké : on vérifie que le SDK Anthropic est bien invoqué
    avec le format messages multimodal attendu."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    fake_client = _install_mock_client(monkeypatch, "Hello from Claude")

    texte = analyser_image(
        "Décris cette photo", b"\x89PNG\r\n", "image/png"
    )
    assert texte == "Hello from Claude"

    # Sanity : on a bien appelé messages.create avec une image en base64
    args, kwargs = fake_client.messages.create.call_args
    msg = kwargs["messages"][0]
    assert msg["role"] == "user"
    content = msg["content"]
    assert len(content) == 2
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    assert content[1]["type"] == "text"
    assert "Décris" in content[1]["text"]


# ---------------------------------------------------------------------------
# analyser_photo_etiquette — service complet (intègre prompt + parse + valid)
# ---------------------------------------------------------------------------


REPONSE_CLAUDE_VALIDE = json.dumps({
    "couleurs_detectees": [
        {
            "rgb_approximatif": "#A23B45",
            "pantone_proche_estime": "186 C",
            "surface_pct": 35,
        },
        {
            "rgb_approximatif": "#FFFFFF",
            "pantone_proche_estime": None,
            "surface_pct": 65,
        },
    ],
    "nombre_couleurs_distinctes": 2,
    "couleurs_min_technique": 2,
    "couleurs_max_technique": 3,
    "techniques_impression_estimees": ["Pantone spot"],
    "matiere_estimee": {
        "type": "papier",
        "couleur": "blanc",
        "finition_apparente": "mat",
    },
    "finitions_visibles": [],
    "presence_blanc_opaque": False,
    "niveau_confiance": "moyen",
    "limites_analyse": ["éclairage smartphone"],
})


def test_analyser_photo_etiquette_happy_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    _install_mock_client(monkeypatch, REPONSE_CLAUDE_VALIDE)

    payload = analyser_photo_etiquette(b"fake-jpeg-bytes", "image/jpeg")

    assert payload["nombre_couleurs_distinctes"] == 2
    assert payload["niveau_confiance"] == "moyen"
    assert len(payload["couleurs_detectees"]) == 2
    assert payload["matiere_estimee"]["type"] == "papier"


def test_analyser_photo_champ_manquant_leve_iaclienterror(monkeypatch):
    """Si Claude renvoie un JSON sans tous les champs CHAMPS_REQUIS → erreur."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    reponse_incomplete = json.dumps({
        "couleurs_detectees": [],
        "nombre_couleurs_distinctes": 0,
        # autres champs requis ABSENTS
    })
    _install_mock_client(monkeypatch, reponse_incomplete)

    with pytest.raises(IAClientError) as exc_info:
        analyser_photo_etiquette(b"fake", "image/jpeg")
    assert "manquants" in str(exc_info.value).lower()


def test_analyser_photo_niveau_confiance_invalide_leve(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    payload: dict[str, Any] = json.loads(REPONSE_CLAUDE_VALIDE)
    payload["niveau_confiance"] = "tres_fort"  # non autorisé
    _install_mock_client(monkeypatch, json.dumps(payload))

    with pytest.raises(IAClientError) as exc_info:
        analyser_photo_etiquette(b"fake", "image/jpeg")
    assert "niveau_confiance" in str(exc_info.value)


def test_analyser_photo_supporte_fence_markdown_dans_reponse(monkeypatch):
    """Robustesse : si Claude enrobe quand même le JSON dans ```json```,
    on parse correctement (via parse_json_strict)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    reponse_avec_fence = f"```json\n{REPONSE_CLAUDE_VALIDE}\n```"
    _install_mock_client(monkeypatch, reponse_avec_fence)

    payload = analyser_photo_etiquette(b"fake", "image/jpeg")
    assert payload["nombre_couleurs_distinctes"] == 2
