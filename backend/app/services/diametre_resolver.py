"""Résolution des valeurs d'entrée du calcul de Ø bobine (bug #6, étape 6.2a).

**Point de calcul unique** : ce module centralise la résolution des DEUX
valeurs qui alimentent le calcul du Ø (helpers géométriques `bat_calculs`
SSOT mm — JAMAIS modifiés ici) :

  1. L'épaisseur effective de la matière (µm) — par lot.
  2. Le Ø de départ de l'enroulement (mm) = Ø mandrin + 2 × paroi mandrin.

Le Ø candidat (étape 2 optimisation) ET le calcul bobines du rebobinage
passent par ces mêmes résolveurs → aucune divergence de valeurs. La paroi
mandrin (`parametre_mandrin.epaisseur_paroi_mm`, ajoutée étape 6.1) est
NULLABLE : `NULL → 0`, ce qui rend l'introduction de la paroi
**non-régressive** (Ø départ = Ø mandrin, comportement actuel).

Aucune formule géométrique ici : on prépare seulement les bonnes valeurs à
passer à `calcul_diametre_bobine` / `calcul_bobines`.
"""
from __future__ import annotations

from typing import Literal

# Épaisseur par défaut quand aucune source fiable n'est disponible (µm).
# Aligné sur `coherence_bobine.EPAISSEUR_FALLBACK_UM` et le défaut historique
# `OptimisationCalculerRequest.epaisseur_matiere_um` (150 µm).
EPAISSEUR_FALLBACK_UM: float = 150.0

# Origine de l'épaisseur retenue — remontée dans le contrat API (transparence).
EpaisseurSource = Literal["matiere", "saisie", "fallback"]


def resoudre_epaisseur_um(
    *,
    matiere_epaisseur_um: float | None,
    saisie_um: float | None = None,
) -> tuple[float, EpaisseurSource]:
    """Résout l'épaisseur effective (µm) et sa source, par priorité.

    Priorité : épaisseur réelle de la matière DU LOT > valeur saisie par
    l'opérateur > fallback 150 µm. Une valeur ≤ 0 est traitée comme absente
    (on passe à la source suivante).

    Args:
      matiere_epaisseur_um : `matiere.epaisseur_microns` du lot (None si pas
        de matière sélectionnée ou colonne NULL au catalogue).
      saisie_um : valeur saisie par l'opérateur (None si non fournie).

    Returns:
      (épaisseur_µm, source) où source ∈ {"matiere", "saisie", "fallback"}.
    """
    if matiere_epaisseur_um is not None and matiere_epaisseur_um > 0:
        return float(matiere_epaisseur_um), "matiere"
    if saisie_um is not None and saisie_um > 0:
        return float(saisie_um), "saisie"
    return EPAISSEUR_FALLBACK_UM, "fallback"


def resoudre_diametre_depart_mm(
    *,
    mandrin_mm: int,
    paroi_mm: int | None = None,
    paroi_override_mm: int | None = None,
) -> tuple[int, int]:
    """Compose le Ø de départ de l'enroulement et la paroi retenue (mm).

    Ø départ = Ø mandrin + 2 × paroi (la paroi s'ajoute des deux côtés du
    diamètre). La paroi est passée tel quel à `calcul_diametre_bobine` /
    `calcul_bobines` COMME `mandrin_mm` — sans toucher la formule.

    Priorité paroi : override opérateur > paroi du `parametre_mandrin` du
    tenant > 0. `NULL/absent → 0` (non-régressif : Ø départ = Ø mandrin).
    Une paroi négative est ignorée (traitée comme absente).

    Args:
      mandrin_mm : Ø intérieur du mandrin (mm).
      paroi_mm : `parametre_mandrin.epaisseur_paroi_mm` (None si non renseigné).
      paroi_override_mm : override ponctuel fourni par l'opérateur (optionnel).

    Returns:
      (diametre_depart_mm, paroi_retenue_mm).
    """
    if paroi_override_mm is not None and paroi_override_mm >= 0:
        paroi = paroi_override_mm
    elif paroi_mm is not None and paroi_mm >= 0:
        paroi = paroi_mm
    else:
        paroi = 0
    return mandrin_mm + 2 * paroi, paroi
