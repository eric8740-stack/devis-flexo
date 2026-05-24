"""Tests du service IA Contrôle BAT — Sprint 15 Lot 2.

Aucun appel réel à l'API Claude — on mock le SDK Anthropic via
monkeypatch (même pattern que `test_ia_analyse_photo.py`).

Couvre :
  - Wrapper `analyser_images` : input invalide (liste vide / bytes vide /
    mime non supporté), happy path multi-images, extraction usage tokens
  - Service `comparer_bat_vs_tirage` : happy path, JSON invalide,
    champ requis manquant, decision_recommandee invalide,
    niveau_confiance_analyse invalide, gravité d'écart invalide,
    calcul coût API > 0, injection sens_demande dans le prompt
"""
import json
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services.ia import client as ia_client
from app.services.ia.client import IAClientError, analyser_images
from app.services.ia.controle_bat import (
    _calculer_cout_eur,
    comparer_bat_vs_tirage,
)


# ---------------------------------------------------------------------------
# Helpers — mock du SDK Anthropic (incluant usage tokens)
# ---------------------------------------------------------------------------


def _mock_anthropic_response(
    texte: str, input_tokens: int = 4000, output_tokens: int = 400
):
    """Construit une fake response conforme à anthropic.Anthropic
    .messages.create — avec usage simulé."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = texte
    response = MagicMock()
    response.content = [text_block]
    response.usage = MagicMock(
        input_tokens=input_tokens, output_tokens=output_tokens
    )
    return response


def _install_mock_client(
    monkeypatch,
    texte_retour: str,
    input_tokens: int = 4000,
    output_tokens: int = 400,
):
    """Remplace `_get_anthropic_client` par un mock qui retourne
    `texte_retour` + un usage simulé."""
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        texte_retour, input_tokens, output_tokens
    )
    monkeypatch.setattr(
        ia_client, "_get_anthropic_client", lambda: fake_client
    )
    return fake_client


# ---------------------------------------------------------------------------
# analyser_images — validations input + happy path
# ---------------------------------------------------------------------------


def test_analyser_images_leve_si_liste_vide(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    with pytest.raises(IAClientError) as exc:
        analyser_images("Hello", images=[])
    assert "aucune image" in str(exc.value).lower()


def test_analyser_images_leve_si_bytes_vides(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    with pytest.raises(IAClientError):
        analyser_images("Hello", images=[(b"", "image/jpeg")])


def test_analyser_images_leve_si_mime_non_supporte(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    with pytest.raises(IAClientError) as exc:
        analyser_images(
            "Hello", images=[(b"\x89PNG", "image/svg+xml")]
        )
    assert "mime_type" in str(exc.value).lower()


def test_analyser_images_happy_path_deux_images_et_usage(monkeypatch):
    """Appel mocké : deux images encodées + usage extrait."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    fake_client = _install_mock_client(
        monkeypatch, "OK", input_tokens=3500, output_tokens=250
    )

    texte, usage = analyser_images(
        "Compare ces deux images.",
        images=[
            (b"\x89PNG\r\n", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
        ],
    )

    assert texte == "OK"
    assert usage == {"input_tokens": 3500, "output_tokens": 250}

    # Sanity : le contenu envoyé a 2 blocs image + 1 bloc texte, dans
    # l'ordre fourni (BAT en premier, tirage en second).
    args, kwargs = fake_client.messages.create.call_args
    content = kwargs["messages"][0]["content"]
    assert len(content) == 3
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    assert content[1]["type"] == "image"
    assert content[1]["source"]["media_type"] == "image/jpeg"
    assert content[2]["type"] == "text"
    assert "Compare" in content[2]["text"]


def test_analyser_images_usage_defaut_a_zero_si_absent(monkeypatch):
    """Si le SDK ne renvoie pas d'attribut usage (ancien SDK / mock
    incomplet), on retourne un dict avec 0/0 plutôt que crasher."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    fake_client = MagicMock()
    text_block = MagicMock(type="text", text="OK")
    response = MagicMock(content=[text_block])
    # Pas d'attribut `usage` sur la response
    del response.usage
    fake_client.messages.create.return_value = response
    monkeypatch.setattr(
        ia_client, "_get_anthropic_client", lambda: fake_client
    )

    _, usage = analyser_images(
        "Hello", images=[(b"\x89PNG", "image/png")]
    )
    assert usage == {"input_tokens": 0, "output_tokens": 0}


# ---------------------------------------------------------------------------
# _calculer_cout_eur — pricing helper
# ---------------------------------------------------------------------------


def test_calculer_cout_eur_positif_pour_appel_typique():
    """Un appel ~4000 tokens input + ~400 tokens output → coût > 0 et
    dans la fourchette annoncée par le brief (0,01-0,10 €)."""
    cout = _calculer_cout_eur(input_tokens=4000, output_tokens=400)
    assert cout > Decimal("0")
    assert cout < Decimal("0.10")


def test_calculer_cout_eur_zero_si_tokens_zero():
    cout = _calculer_cout_eur(input_tokens=0, output_tokens=0)
    assert cout == Decimal("0.0000")


def test_calculer_cout_eur_quantize_4_decimales():
    """Doit s'arrondir à 4 décimales (cohérent NUMERIC(6,4))."""
    cout = _calculer_cout_eur(input_tokens=1234, output_tokens=567)
    # Vérifie que l'exposant Decimal est bien -4 (4 décimales).
    assert -cout.as_tuple().exponent == 4


# ---------------------------------------------------------------------------
# Fixtures payloads Claude valide
# ---------------------------------------------------------------------------


REPONSE_BAT_VALIDE_DICT: dict[str, Any] = {
    "score_conformite_global": 92,
    "decision_recommandee": "valider",
    "ecarts_detectes": [
        {
            "type": "couleur",
            "gravite": "mineur",
            "localisation": "bandeau bas",
            "description": "Légère dérive du jaune",
            "suggestion_correction": "Ajuster densité jaune station 3",
        }
    ],
    "elements_conformes": ["Disposition globale", "Découpe contour"],
    "elements_manquants": [],
    "niveau_confiance_analyse": "haut",
    "limites_analyse": [],
    "sens_sortie_detecte": {
        "orientation_etiquette": "tête en haut",
        "sens_lecture": "gauche-vers-droite",
        "sens_enroulement_resultant": "SE1",
        "coherence_avec_bat": True,
    },
    "alerte_sens_enroulement": None,
}


def _reponse_str(modifs: dict | None = None) -> str:
    """Sérialise une réponse Claude éventuellement modifiée."""
    payload = json.loads(json.dumps(REPONSE_BAT_VALIDE_DICT))
    if modifs:
        payload.update(modifs)
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# comparer_bat_vs_tirage — happy path + validations
# ---------------------------------------------------------------------------


def test_comparer_bat_vs_tirage_happy_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    _install_mock_client(monkeypatch, _reponse_str())

    payload = comparer_bat_vs_tirage(
        bat_image_bytes=b"fake-bat",
        tirage_image_bytes=b"fake-tirage",
    )

    assert payload["score_conformite_global"] == 92
    assert payload["decision_recommandee"] == "valider"
    assert payload["niveau_confiance_analyse"] == "haut"
    assert payload["sens_sortie_detecte"]["sens_enroulement_resultant"] == "SE1"
    assert payload["alerte_sens_enroulement"] is None
    # Coût calculé > 0 (usage par défaut 4000 input + 400 output dans le mock)
    assert payload["cout_api_eur"] > Decimal("0")


def test_comparer_bat_vs_tirage_json_invalide_leve(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    _install_mock_client(monkeypatch, "ceci n'est pas du JSON valide")
    with pytest.raises(IAClientError) as exc:
        comparer_bat_vs_tirage(b"bat", b"tirage")
    assert "JSON valide" in str(exc.value)


def test_comparer_bat_vs_tirage_champ_manquant_leve(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    payload = dict(REPONSE_BAT_VALIDE_DICT)
    del payload["sens_sortie_detecte"]
    _install_mock_client(monkeypatch, json.dumps(payload))
    with pytest.raises(IAClientError) as exc:
        comparer_bat_vs_tirage(b"bat", b"tirage")
    assert "manquants" in str(exc.value).lower()
    assert "sens_sortie_detecte" in str(exc.value)


def test_comparer_bat_vs_tirage_decision_invalide_leve(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    _install_mock_client(
        monkeypatch, _reponse_str({"decision_recommandee": "yolo"})
    )
    with pytest.raises(IAClientError) as exc:
        comparer_bat_vs_tirage(b"bat", b"tirage")
    assert "decision_recommandee" in str(exc.value)


def test_comparer_bat_vs_tirage_niveau_confiance_invalide_leve(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    _install_mock_client(
        monkeypatch,
        _reponse_str({"niveau_confiance_analyse": "tres_fort"}),
    )
    with pytest.raises(IAClientError) as exc:
        comparer_bat_vs_tirage(b"bat", b"tirage")
    assert "niveau_confiance_analyse" in str(exc.value)


def test_comparer_bat_vs_tirage_gravite_ecart_invalide_leve(monkeypatch):
    """Un écart avec gravité non autorisée → IAClientError."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    payload = json.loads(json.dumps(REPONSE_BAT_VALIDE_DICT))
    payload["ecarts_detectes"][0]["gravite"] = "catastrophique"
    _install_mock_client(monkeypatch, json.dumps(payload))
    with pytest.raises(IAClientError) as exc:
        comparer_bat_vs_tirage(b"bat", b"tirage")
    assert "gravite" in str(exc.value)


def test_comparer_bat_vs_tirage_type_ecart_invalide_leve(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    payload = json.loads(json.dumps(REPONSE_BAT_VALIDE_DICT))
    payload["ecarts_detectes"][0]["type"] = "saveur"
    _install_mock_client(monkeypatch, json.dumps(payload))
    with pytest.raises(IAClientError) as exc:
        comparer_bat_vs_tirage(b"bat", b"tirage")
    assert "type" in str(exc.value).lower()


def test_comparer_bat_vs_tirage_supporte_ecarts_vides(monkeypatch):
    """Liste d'écarts vide = aucun écart détecté → ne lève pas."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    _install_mock_client(
        monkeypatch, _reponse_str({"ecarts_detectes": []})
    )
    payload = comparer_bat_vs_tirage(b"bat", b"tirage")
    assert payload["ecarts_detectes"] == []


def test_comparer_bat_vs_tirage_supporte_fence_markdown(monkeypatch):
    """Si Claude enrobe le JSON dans ```json``` malgré l'instruction → on
    parse via parse_json_strict (robustesse héritée du wrapper)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    _install_mock_client(monkeypatch, f"```json\n{_reponse_str()}\n```")
    payload = comparer_bat_vs_tirage(b"bat", b"tirage")
    assert payload["score_conformite_global"] == 92


def test_comparer_bat_vs_tirage_injecte_sens_demande_dans_prompt(monkeypatch):
    """sens_demande="SE3" → préfixe "Sens demandé : SE3" dans le prompt."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    fake_client = _install_mock_client(monkeypatch, _reponse_str())

    comparer_bat_vs_tirage(
        bat_image_bytes=b"bat",
        tirage_image_bytes=b"tirage",
        sens_demande="SE3",
    )

    args, kwargs = fake_client.messages.create.call_args
    content = kwargs["messages"][0]["content"]
    # Le dernier bloc est le texte ; il doit commencer par le contexte injecté
    texte = content[-1]["text"]
    assert texte.startswith("Contexte : Sens demandé : SE3")


def test_comparer_bat_vs_tirage_sans_sens_demande_pas_de_prefixe(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    fake_client = _install_mock_client(monkeypatch, _reponse_str())

    comparer_bat_vs_tirage(
        bat_image_bytes=b"bat",
        tirage_image_bytes=b"tirage",
        sens_demande=None,
    )

    args, kwargs = fake_client.messages.create.call_args
    texte = kwargs["messages"][0]["content"][-1]["text"]
    assert not texte.startswith("Contexte :")
    assert "expert en contrôle qualité" in texte.lower()


def test_comparer_bat_vs_tirage_cible_modele_sonnet(monkeypatch):
    """Vérifie que le service appelle bien claude-sonnet (cf. brief Lot 2)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    fake_client = _install_mock_client(monkeypatch, _reponse_str())

    comparer_bat_vs_tirage(b"bat", b"tirage")

    args, kwargs = fake_client.messages.create.call_args
    assert "sonnet" in kwargs["model"].lower()
