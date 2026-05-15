"""Tests heuristique support_reserve (fix analyseur photo).

Couvre :
  - is_support_reserve() : 3 conditions cumulatives + cas seuil RGB
  - hex_to_rgb() : parsing avec/sans '#', invalides
  - appliquer_support_reserve() : mutation in-place du payload + recalcul
    compteurs stations
"""
import pytest

from app.services.ia.support_reserve import (
    OPAQUE_LIGHT_SUPPORTS,
    SEUIL_BLANC_RGB,
    appliquer_support_reserve,
    hex_to_rgb,
    is_support_reserve,
)


# ---------------------------------------------------------------------------
# hex_to_rgb
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hex_val,rgb_attendu",
    [
        ("#FFFFFF", (255, 255, 255)),
        ("#000000", (0, 0, 0)),
        ("#A23B45", (162, 59, 69)),
        ("FFFFFF", (255, 255, 255)),  # sans #
        (" #F8F8F8 ", (248, 248, 248)),  # avec espaces
    ],
)
def test_hex_to_rgb_valid(hex_val, rgb_attendu):
    assert hex_to_rgb(hex_val) == rgb_attendu


@pytest.mark.parametrize("invalid", ["#FFF", "#ZZZZZZ", "FFFFFFAA", "", "no"])
def test_hex_to_rgb_invalid_raises(invalid):
    with pytest.raises(ValueError):
        hex_to_rgb(invalid)


# ---------------------------------------------------------------------------
# is_support_reserve — 3 cas du brief + cas seuil
# ---------------------------------------------------------------------------


def test_white_on_white_paper_is_reserve():
    """Cas 1 du brief : #FFFFFF sur papier blanc → True (réserve)."""
    assert is_support_reserve("#FFFFFF", "papier", "blanc") is True


def test_white_on_transparent_film_is_ink():
    """Cas 2 du brief : #FFFFFF sur film transparent → False (encre)."""
    assert is_support_reserve("#FFFFFF", "PE", "transparent") is False


def test_threshold_quasi_white():
    """Cas 3 du brief : seuil RGB 240.
    F8F8F8 (248) → réserve. E0E0E0 (224) → encre (sous seuil)."""
    assert is_support_reserve("#F8F8F8", "papier", "blanc") is True
    assert is_support_reserve("#E0E0E0", "papier", "blanc") is False


def test_threshold_borderline_exact():
    """Pile au seuil = inclusif (>= 240)."""
    assert is_support_reserve("#F0F0F0", "papier", "blanc") is True  # 240
    assert is_support_reserve("#EFEFEF", "papier", "blanc") is False  # 239


def test_all_opaque_light_supports_couverts():
    """Tous les supports opaques clairs déclenchent la règle."""
    for support in OPAQUE_LIGHT_SUPPORTS:
        assert is_support_reserve("#FFFFFF", support, "blanc") is True


def test_support_colore_meme_clair_pas_reserve():
    """Support coloré → toujours encre (même si zone blanche détectée)."""
    assert is_support_reserve("#FFFFFF", "papier", "colore") is False
    assert is_support_reserve("#FFFFFF", "papier", "metallise") is False
    assert is_support_reserve("#FFFFFF", "papier", "inconnu") is False


def test_support_inconnu_pas_reserve():
    """Si Claude n'a pas pu identifier le support → ne pas marquer
    réserve (préférable de surfacturer qu'inverse)."""
    assert is_support_reserve("#FFFFFF", "inconnu", "blanc") is False


def test_hex_invalide_pas_reserve():
    """Hex non parsable → False (ne pas crasher, ne pas flagger)."""
    assert is_support_reserve("bad-hex", "papier", "blanc") is False


def test_seuil_constant_documente():
    """Sanity : le seuil reste 240, valeur du brief."""
    assert SEUIL_BLANC_RGB == 240


# ---------------------------------------------------------------------------
# appliquer_support_reserve — mutation payload + recalcul compteurs
# ---------------------------------------------------------------------------


def _payload_typique(matiere_type="papier", matiere_couleur="blanc"):
    """Construit un payload Claude type pour les tests d'intégration."""
    return {
        "couleurs_detectees": [
            {"rgb_approximatif": "#FFFFFF", "surface_pct": 60},
            {"rgb_approximatif": "#A23B45", "surface_pct": 25},
            {"rgb_approximatif": "#0F4C81", "surface_pct": 15},
        ],
        "nombre_couleurs_distinctes": 3,
        "couleurs_min_technique": 3,
        "couleurs_max_technique": 5,
        "matiere_estimee": {
            "type": matiere_type,
            "couleur": matiere_couleur,
            "finition_apparente": "mat",
        },
    }


def test_appliquer_flag_blanc_sur_papier_blanc():
    """Réserve : flag posé + min/max décrémentés."""
    payload = _payload_typique(matiere_type="papier", matiere_couleur="blanc")
    appliquer_support_reserve(payload)

    couleurs = payload["couleurs_detectees"]
    assert couleurs[0]["support_reserve"] is True  # blanc → réserve
    assert couleurs[1]["support_reserve"] is False  # rouge → encre
    assert couleurs[2]["support_reserve"] is False  # bleu → encre
    # 1 réserve retirée des compteurs : 3 → 2, 5 → 4
    assert payload["couleurs_min_technique"] == 2
    assert payload["couleurs_max_technique"] == 4
    # Nombre total inchangé (UI doit afficher les 3 cards avec badges)
    assert payload["nombre_couleurs_distinctes"] == 3
    assert len(payload["couleurs_detectees"]) == 3


def test_appliquer_blanc_sur_transparent_reste_encre():
    """Blanc sur film transparent → pas réserve, compteurs inchangés."""
    payload = _payload_typique(matiere_type="PE", matiere_couleur="transparent")
    appliquer_support_reserve(payload)

    for c in payload["couleurs_detectees"]:
        assert c["support_reserve"] is False
    assert payload["couleurs_min_technique"] == 3
    assert payload["couleurs_max_technique"] == 5


def test_appliquer_pas_de_blanc_pas_de_changement():
    """Aucun blanc détecté → tous flaggés False, compteurs inchangés."""
    payload = {
        "couleurs_detectees": [
            {"rgb_approximatif": "#A23B45", "surface_pct": 60},
            {"rgb_approximatif": "#0F4C81", "surface_pct": 40},
        ],
        "nombre_couleurs_distinctes": 2,
        "couleurs_min_technique": 2,
        "couleurs_max_technique": 3,
        "matiere_estimee": {
            "type": "papier",
            "couleur": "blanc",
            "finition_apparente": "mat",
        },
    }
    appliquer_support_reserve(payload)
    for c in payload["couleurs_detectees"]:
        assert c["support_reserve"] is False
    assert payload["couleurs_min_technique"] == 2
    assert payload["couleurs_max_technique"] == 3


def test_appliquer_couleurs_detectees_vide():
    """Edge case : palette vide ne crashe pas."""
    payload = {
        "couleurs_detectees": [],
        "nombre_couleurs_distinctes": 0,
        "couleurs_min_technique": 0,
        "couleurs_max_technique": 0,
        "matiere_estimee": {"type": "papier", "couleur": "blanc"},
    }
    appliquer_support_reserve(payload)
    assert payload["couleurs_min_technique"] == 0
    assert payload["couleurs_max_technique"] == 0


def test_appliquer_compteur_min_jamais_negatif():
    """Si Claude a sous-évalué min_stations et qu'on retire plus que
    présent → on borne à 0 (pas de valeur négative)."""
    payload = {
        "couleurs_detectees": [
            {"rgb_approximatif": "#FFFFFF", "surface_pct": 50},
            {"rgb_approximatif": "#F8F8F8", "surface_pct": 50},
        ],
        "nombre_couleurs_distinctes": 2,
        "couleurs_min_technique": 1,  # sous-évalué
        "couleurs_max_technique": 1,
        "matiere_estimee": {"type": "papier", "couleur": "blanc"},
    }
    appliquer_support_reserve(payload)
    # 2 réserves détectées, on retire 2 d'un compteur à 1 → max(0, -1) = 0
    assert payload["couleurs_min_technique"] == 0
    assert payload["couleurs_max_technique"] == 0


def test_appliquer_chainable_retourne_payload():
    """La fonction retourne le payload pour permettre le chaînage."""
    payload = _payload_typique()
    assert appliquer_support_reserve(payload) is payload
