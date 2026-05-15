"""Règle effet banane Sprint 13 S13.D.1 — FILTRE DUR.

Plus la plaque est large, plus elle nécessite un cylindre magnétique
avec un développé minimum pour ne pas se déformer en arc sur le cylindre
(CdC § 556-581). C'est mécanique : une plaque large sur un petit cylindre
se courbe en banane sous la pression et dégrade qualité d'impression
et de découpe.

Filtre dur : un cylindre exclu est définitivement exclu — pas de
compromis possible. La règle est appliquée EN PREMIER (avant échenillage)
pour ne pas calculer un score sur un cylindre éliminé d'office.

Le barème est paramétrable par imprimerie (table bareme.type='effet_banane',
JSON). Le barème ICE par défaut (paliers à 150/200/250/300/350 mm) est
non-linéaire — saut Z=120 → Z=160 entre 250-300 et 300-350 mm (seuil
physique de rigidité). Cette donnée empirique ne peut pas être extrapolée
par formule.
"""
from __future__ import annotations

from typing import Any

from app.services.optimisation.types import Cylindre, FiltreResult


def lookup_developpe_mini(
    largeur_plaque_mm: float, bareme: list[dict[str, Any]]
) -> float:
    """Renvoie le développé cylindre minimum requis pour cette largeur.

    Le barème est une liste de paliers triés par `largeur_max_mm`
    croissante. On retourne le `developpe_mini_mm` du PREMIER palier
    dont `largeur_max_mm >= largeur_plaque_mm`. Au-delà du dernier
    palier, on prend le `developpe_mini_mm` du dernier (extrapolation
    plateau — CdC ligne 576 "> 350 → 160").

    Barème vide → 0 (pas de contrainte, tout passe).
    """
    if not bareme:
        return 0.0
    for palier in bareme:
        if largeur_plaque_mm <= palier["largeur_max_mm"]:
            return float(palier["developpe_mini_mm"])
    # Au-delà du dernier palier → on prend son developpe_mini_mm (plateau)
    return float(bareme[-1]["developpe_mini_mm"])


def valide_effet_banane(
    cylindre: Cylindre,
    largeur_plaque_mm: float,
    bareme: list[dict[str, Any]],
) -> FiltreResult:
    """Vérifie qu'un cylindre est compatible avec la largeur de plaque.

    Renvoie FiltreResult(ok=True) si développé >= Z mini requis.
    Sinon FiltreResult(ok=False, raison='effet_banane', message=...).

    Sémantique seuil : développé == Z mini → OK (inclusion).
    """
    z_mini = lookup_developpe_mini(largeur_plaque_mm, bareme)
    if cylindre.developpe_mm >= z_mini:
        return FiltreResult(ok=True)
    return FiltreResult(
        ok=False,
        raison="effet_banane",
        message=(
            f"Cylindre {cylindre.developpe_mm} mm exclu : "
            f"plaque de {largeur_plaque_mm:.1f} mm requiert "
            f"un développé minimum de {z_mini} mm."
        ),
    )
