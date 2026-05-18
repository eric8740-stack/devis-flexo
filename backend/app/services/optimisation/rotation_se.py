"""Mapping des rotations du A selon le sens d'enroulement (8 sens ICE).

Convention métier "X avant" = côté X de l'étiquette pointe vers AVANCE
machine en sortie de presse. Deux mappings indépendants :

VUE A — plaque vue sens machine. L'AVANCE est verticale (vers le bas).
Le côté désigné par le sens (droite/gauche/pied/tête) doit pointer vers
le bas de l'image :
    Sens 1/5 (droite avant) → A couché tête à gauche  → rotation 270°
    Sens 2/6 (gauche avant) → A couché tête à droite  → rotation 90°
    Sens 3/7 (pied avant)   → A debout normal         → rotation 0°
    Sens 4/8 (tête avant)   → A renversé tête en bas  → rotation 180°

VUE C — bobine fille déroulée chez le client. Le déroulement est
horizontal (vers la droite, sens client). Le côté désigné par le sens
doit pointer vers la droite de l'image. La rotation VUE C est donc
décalée de +90° par rapport à la VUE A :
    Sens 1/5 (droite avant) → A debout (droite vers la droite)  → 0°
    Sens 2/6 (gauche avant) → A renversé                        → 180°
    Sens 3/7 (pied avant)   → A couché tête à gauche            → 90°
    Sens 4/8 (tête avant)   → A couché tête à droite            → 270°

Les paires extérieur/intérieur (1/5, 2/6, 3/7, 4/8) partagent **la
même rotation** : seule la face (dehors vs dedans) diffère, et cette
distinction est portée par la VUE B (illustration bobine livrée) +
le badge texte. La rotation du A est purement géométrique.
"""
from typing import Literal


SensEnroulement = Literal[
    "SE1", "SE2", "SE3", "SE4", "SE5", "SE6", "SE7", "SE8"
]


ROTATION_VUE_A: dict[str, int] = {
    "SE1": 270, "SE2": 90, "SE3": 0, "SE4": 180,
    "SE5": 270, "SE6": 90, "SE7": 0, "SE8": 180,
}


ROTATION_VUE_C: dict[str, int] = {
    "SE1": 0, "SE2": 180, "SE3": 90, "SE4": 270,
    "SE5": 0, "SE6": 180, "SE7": 90, "SE8": 270,
}


def rotation_vue_a_deg(se: str) -> int:
    """Rotation du A pour la VUE A (sens machine). Lève KeyError si SE inconnu."""
    return ROTATION_VUE_A[se]


def rotation_vue_c_deg(se: str) -> int:
    """Rotation du A pour la VUE C (bobine fille déroulée chez le client)."""
    return ROTATION_VUE_C[se]
