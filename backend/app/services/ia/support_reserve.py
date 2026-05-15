"""Heuristique support_reserve — fix analyseur photo.

Distingue le blanc "réserve papier" (défonce sur support opaque clair)
du blanc "encre d'opacité" (encre blanche imprimée sur support transparent
ou coloré).

Règle métier flexo :
  - Support blanc opaque + zone blanche détectée → réserve papier
    (0 station, 0 surcoût encre)
  - Support transparent / coloré + zone blanche détectée → encre blanche
    d'opacité (+1 station d'impression)

Sans cette heuristique, l'analyseur surévaluait d'une station tous les
visuels à défonce blanche sur papier blanc — soit la majorité des
étiquettes alimentaires.

L'utilisateur peut OVERRIDE le flag côté UI (toggle "Considérer comme
encre blanche") — l'API ne fait que poser le defaut métier raisonnable.
"""
from __future__ import annotations

from typing import Any


# Supports opaques clairs où une zone blanche détectée est plus probablement
# une réserve papier qu'une encre blanche imprimée.
# Notre schéma matiere_estimee.type provient du prompt Claude
# (cf. prompts/analyse_photo.txt) :
#   "papier" | "BOPP" | "PET" | "PE" | "thermique" | "synthetique" | "inconnu"
# Tous sauf "inconnu" peuvent être blanc opaque selon matiere.couleur.
OPAQUE_LIGHT_SUPPORTS = frozenset(
    {"papier", "BOPP", "PET", "PE", "thermique", "synthetique"}
)

# Seuil RGB en dessous duquel on ne considère plus comme "blanc". 240/255
# correspond à ~94% luminosité — couvre les blancs cassés / éclairages
# tièdes sans déborder sur les gris clairs (#E0E0E0 = 224 reste exclu).
SEUIL_BLANC_RGB = 240


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convertit '#RRGGBB' (ou 'RRGGBB') en (R, G, B) entiers 0-255.

    Lève ValueError si format invalide.
    """
    h = hex_color.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"hex invalide (attendu 6 chars) : {hex_color!r}")
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError as exc:
        raise ValueError(f"hex non parsable : {hex_color!r}") from exc


def is_support_reserve(
    color_hex: str, support_type: str, support_couleur: str
) -> bool:
    """True si la teinte correspond à la réserve papier.

    Trois conditions cumulatives :
      1. Support ∈ opaques clairs (papier, BOPP, PET, PE, thermique, synthetique)
      2. Couleur du support = "blanc"
      3. Teinte quasi-blanche : R, G, B tous ≥ 240

    Si l'une manque → False (= encre, à compter dans les stations).
    Hex invalide → False (on préfère compter en station que rater une
    encre — c'est moins grave de surfacturer un blanc que de sous-facturer).
    """
    if support_type not in OPAQUE_LIGHT_SUPPORTS:
        return False
    if support_couleur != "blanc":
        return False
    try:
        r, g, b = hex_to_rgb(color_hex)
    except ValueError:
        return False
    return min(r, g, b) >= SEUIL_BLANC_RGB


def appliquer_support_reserve(payload: dict[str, Any]) -> dict[str, Any]:
    """Post-traite la réponse Claude pour flagger les réserves papier et
    recalculer les compteurs de stations.

    Mutations IN PLACE sur le payload :
      - Chaque entrée de `couleurs_detectees` reçoit `support_reserve: bool`
      - `couleurs_min_technique` et `couleurs_max_technique` sont diminués
        du nombre de couleurs flaguées réserve (sans descendre sous 0)

    Important : on ne touche pas à `nombre_couleurs_distinctes` ni à
    `couleurs_detectees` lui-même — l'UI doit afficher TOUTES les couleurs
    détectées (avec le badge approprié) et le compteur (N) correspond
    bien à `len(couleurs_detectees)` côté front.

    Retourne le payload pour permettre le chaînage.
    """
    matiere = payload.get("matiere_estimee") or {}
    support_type = matiere.get("type", "inconnu")
    support_couleur = matiere.get("couleur", "inconnu")

    nb_reserves = 0
    for couleur in payload.get("couleurs_detectees", []):
        hex_val = couleur.get("rgb_approximatif", "")
        reserve = is_support_reserve(hex_val, support_type, support_couleur)
        couleur["support_reserve"] = reserve
        if reserve:
            nb_reserves += 1

    if nb_reserves > 0:
        # On retire les réserves des compteurs de stations : Claude tend à
        # les inclure (il voit une "couleur" dans la palette même si c'est
        # le support). Si Claude ne les avait pas comptées, max(0, ...)
        # évite de descendre sous 0.
        payload["couleurs_min_technique"] = max(
            0, int(payload.get("couleurs_min_technique", 0)) - nb_reserves
        )
        payload["couleurs_max_technique"] = max(
            0, int(payload.get("couleurs_max_technique", 0)) - nb_reserves
        )

    return payload
