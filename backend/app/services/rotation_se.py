"""Mapping des rotations VUE A et VUE C pour les 8 sens d'enroulement.

Convention métier flexographique officielle, verrouillée le 18/05/2026 :
- VUE A représente la planche presse (vertical, AVANCE pointant vers le bas).
- VUE C représente la bobine fille déroulée chez le client (horizontal,
  défilement vers la droite).
- Les paires extérieur/intérieur (1/5, 2/6, 3/7, 4/8) partagent les MÊMES
  rotations VUE A et VUE C ; la seule différence est la face imprimée
  (dedans/dehors), visible uniquement sur la VUE B (rouleau 3D Canva).

Importance critique : la VUE A est utilisée par le poseur de cliché pour
orienter le cliché physique sur la presse. Si elle est fausse → cliché
posé à l'envers → tirage entier à jeter. Le futur module BAT IA
(Sprint 14) comparera des photos de sortie machine avec cette VUE A —
elle doit être physiquement exacte.

Rotation SVG horaire (transform="rotate(angle cx cy)") :
    0°   = tête haut
    90°  = tête droite
    180° = tête bas
    270° = tête gauche
"""
from typing import Literal


# Type accepté en argument côté backend : int (1-8). Le router convertit
# depuis Literal["SE1"..."SE8"] via `int(se.replace("SE", ""))`.
SensInt = Literal[1, 2, 3, 4, 5, 6, 7, 8]


ROTATION_VUE_A: dict[int, int] = {
    1: 90,
    2: 270,
    3: 0,
    4: 180,
    5: 90,
    6: 270,
    7: 0,
    8: 180,
}


ROTATION_VUE_C: dict[int, int] = {
    1: 0,
    2: 180,
    3: 270,
    4: 90,
    5: 0,
    6: 180,
    7: 270,
    8: 90,
}


LIBELLES_OFFICIELS: dict[int, str] = {
    1: "0° Extérieur droite avant",
    2: "180° Extérieur gauche avant",
    3: "270° Extérieur pied avant",
    4: "90° Extérieur tête avant",
    5: "0° Intérieur droite avant",
    6: "180° Intérieur gauche avant",
    7: "270° Intérieur pied avant",
    8: "90° Intérieur tête avant",
}


def _valider(sens_enroulement: int) -> None:
    if sens_enroulement not in ROTATION_VUE_A:
        raise ValueError(
            f"sens_enroulement doit être entre 1 et 8, reçu {sens_enroulement}"
        )


def get_rotation_vue_a(sens_enroulement: int) -> int:
    """Rotation à appliquer au A en VUE A (planche presse, sens machine).

    Args:
        sens_enroulement: Entier de 1 à 8.

    Returns:
        Rotation en degrés (0, 90, 180 ou 270).

    Raises:
        ValueError: Si sens_enroulement hors de [1, 8].
    """
    _valider(sens_enroulement)
    return ROTATION_VUE_A[sens_enroulement]


def get_rotation_vue_c(sens_enroulement: int) -> int:
    """Rotation à appliquer au A en VUE C (bobine fille déroulée client)."""
    _valider(sens_enroulement)
    return ROTATION_VUE_C[sens_enroulement]


def get_libelle_officiel(sens_enroulement: int) -> str:
    """Libellé officiel du sens à afficher dans le BAT et le formulaire."""
    _valider(sens_enroulement)
    return LIBELLES_OFFICIELS[sens_enroulement]
