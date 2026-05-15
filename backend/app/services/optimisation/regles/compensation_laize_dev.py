"""Règle compensation laize/dev Sprint 13 S13.D.3 — BONUS.

CdC § 531-554 : quand on est forcé d'avoir un grand intervalle dev
(cylindre non idéal), le squelette devient fragile dans le sens du
déroulé. Pour le consolider, on peut ÉLARGIR l'intervalle laize (entre
colonnes d'étiquettes) afin d'avoir plus de matière transverse qui tient
l'ensemble.

C'est un trade-off géré par l'orchestrateur : on perd potentiellement
une pose laize mais on récupère de la vitesse machine.

Le barème ICE par défaut :
  dev ≤ 4 mm     → aucun bonus (déjà optimal)
  dev = 5 mm     → laize ≥ 4 mm : coef vitesse 0.70 → 0.85
  dev = 6 mm     → laize ≥ 5 mm : coef vitesse 0.60 → 0.80
  dev 7-8 mm     → laize ≥ 6 mm : coef vitesse 0.50 → 0.70
  dev > 8 mm     → laize ≥ 70 % du dev : coef vitesse 0.40 → 0.60

API :
  - lookup_palier_compensation(dev_mm, bareme) -> palier
        Retourne le palier qui couvre cet intervalle dev (peut avoir
        intervalle_laize_souhaitable_mm fixe OU pct_dev pour > 8 mm).

  - evaluer_compensation(dev_mm, laize_mm, bareme) -> dict
        consolidation_atteinte:bool, coef_vitesse_si_atteint:float|None,
        intervalle_laize_souhaitable_mm:float|None.
        Si consolidation_atteinte=True, l'orchestrateur remplacera le
        coef_vitesse_echenillage standard par coef_vitesse_si_atteint.
"""
from __future__ import annotations

from typing import Any


PALIER_NEUTRE = {
    "intervalle_dev_min_mm": 0,
    "intervalle_dev_max_mm": float("inf"),
    "intervalle_laize_souhaitable_mm": None,
    "coef_vitesse_si_atteint": None,
    "notes": "Bareme non configure",
}


def lookup_palier_compensation(
    intervalle_dev_mm: float, bareme: list[dict[str, Any]]
) -> dict[str, Any]:
    """Renvoie le palier qui couvre intervalle_dev_mm dans le barème.

    Le barème est une liste de paliers triés par intervalle_dev_min_mm
    croissant. Le palier qui correspond est celui dont l'intervalle
    [min, max) contient intervalle_dev_mm.

    Convention seuil : on prend le palier dont
    intervalle_dev_mm <= intervalle_dev_max_mm (max inclusif côté droit).
    """
    if not bareme:
        return PALIER_NEUTRE.copy()
    for palier in bareme:
        max_mm = palier.get("intervalle_dev_max_mm", float("inf"))
        if intervalle_dev_mm <= max_mm:
            return palier
    return bareme[-1]


def evaluer_compensation(
    intervalle_dev_mm: float,
    intervalle_laize_mm: float,
    bareme: list[dict[str, Any]],
) -> dict[str, Any]:
    """Détermine si la consolidation est atteinte pour cette config.

    Retour :
      - consolidation_atteinte : bool
      - coef_vitesse_si_atteint : float|None (le coef à appliquer si
        consolidation atteinte, qui REMPLACE le coef vitesse échenillage
        standard. None si pas de bonus possible — palier "déjà optimal"
        ou barème vide.)
      - intervalle_laize_souhaitable_mm : float|None — le seuil minimum
        de laize qui aurait débloqué le bonus (pour message UI).
    """
    palier = lookup_palier_compensation(intervalle_dev_mm, bareme)

    coef = palier.get("coef_vitesse_si_atteint")
    seuil_mm: float | None = palier.get("intervalle_laize_souhaitable_mm")

    # Cas palier "> 8 mm" : seuil = pct_dev × dev
    pct_dev = palier.get("intervalle_laize_souhaitable_pct_dev")
    if seuil_mm is None and pct_dev is not None:
        seuil_mm = float(pct_dev) / 100.0 * intervalle_dev_mm

    if coef is None:
        # Palier "déjà optimal" — pas de bonus à appliquer même si laize
        # serait largement suffisante.
        return {
            "consolidation_atteinte": False,
            "coef_vitesse_si_atteint": None,
            "intervalle_laize_souhaitable_mm": seuil_mm,
        }

    atteinte = seuil_mm is not None and intervalle_laize_mm >= seuil_mm
    return {
        "consolidation_atteinte": atteinte,
        "coef_vitesse_si_atteint": coef if atteinte else None,
        "intervalle_laize_souhaitable_mm": seuil_mm,
    }
