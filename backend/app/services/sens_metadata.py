"""Façade pour les métadonnées d'un sens d'enroulement (libellé + rotations
VUE A / VUE C), couvrant les **10** sens supportés par l'UI optim :

- Sens 1-8 : convention métier flexo verrouillée (cliché posé, orientations
  physiques). Délégué à `rotation_se` (module SACRÉ, intact).
- Sens 0 / 9 : bobines livrées VIERGES, sans impression. Pas de cliché →
  pas d'orientation à représenter (rotation = 0). Géré ici directement,
  hors de `rotation_se` pour préserver le verrouillage 1-8 de ce dernier.

Tous les call sites qui consommaient `rotation_se.get_libelle_officiel` /
`get_rotation_vue_a` / `get_rotation_vue_c` passent désormais par cette
façade — ainsi un lot SE0/SE9 ne lève plus `ValueError` à la création.
"""
from app.services.rotation_se import (
    get_libelle_officiel as _get_libelle_8,
    get_rotation_vue_a as _get_rot_a_8,
    get_rotation_vue_c as _get_rot_c_8,
)


_LIBELLES_VIERGES: dict[int, str] = {
    0: "0° Extérieur · sans impression",
    9: "0° Intérieur · sans impression",
}


def is_sens_vierge(sens_enroulement: int) -> bool:
    """True si le sens correspond à une bobine livrée vierge (0 ou 9)."""
    return sens_enroulement in _LIBELLES_VIERGES


def get_libelle_officiel(sens_enroulement: int) -> str:
    """Libellé officiel pour les 10 sens. Délègue à rotation_se pour 1-8."""
    if sens_enroulement in _LIBELLES_VIERGES:
        return _LIBELLES_VIERGES[sens_enroulement]
    return _get_libelle_8(sens_enroulement)


def get_rotation_vue_a(sens_enroulement: int) -> int:
    """Rotation VUE A (planche presse). 0 pour les sens vierges."""
    if sens_enroulement in _LIBELLES_VIERGES:
        return 0
    return _get_rot_a_8(sens_enroulement)


def get_rotation_vue_c(sens_enroulement: int) -> int:
    """Rotation VUE C (bobine fille déroulée client). 0 pour les sens vierges."""
    if sens_enroulement in _LIBELLES_VIERGES:
        return 0
    return _get_rot_c_8(sens_enroulement)
