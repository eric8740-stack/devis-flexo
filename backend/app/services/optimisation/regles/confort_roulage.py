"""Règle confort roulage Sprint 13 S13.D.4 — COEFS RAYON + QUINCONCE.

CdC § 716-784 : un outil de découpe en rotation subit la physique d'une
roue qui aborde un trottoir. Plus les angles d'attaque sont vifs, plus
chaque tour génère un choc qui force à ralentir la machine et use l'outil.

Deux paramètres indépendants se cumulent multiplicativement :

  1. coef_rayon : fonction du rayon des angles (0=vif, plus c'est grand
     mieux c'est). Forme ronde/ovale → 1.15 indépendamment du rayon.

  2. coef_quinconce : pose alignée (1.00) ou décalée 1 ligne sur 2 (1.10).
     Le quinconce est INVISIBLE pour le client final (CdC ligne 749) —
     l'imprimeur peut l'activer librement sans accord client.

Barème structure (différente des autres règles — dict avec sous-listes) :
  {
    "bareme_rayon": [{rayon_max_mm, coef}, ...],
    "coef_forme_courbe": 1.15,
    "coef_quinconce": 1.10,
  }
"""
from __future__ import annotations

from typing import Any


def coef_confort_rayon(
    rayon_mm: float, forme_courbe: bool, bareme: dict[str, Any]
) -> float:
    """Retourne le coefficient de confort de roulage selon le rayon
    (et override si forme courbe = rond/ovale).

    `bareme` est un dict avec :
      - "bareme_rayon" : liste de paliers triés par rayon_max_mm croissant
      - "coef_forme_courbe" : coef à appliquer si forme_courbe=True

    Si forme_courbe → on retourne coef_forme_courbe directement, le rayon
    n'a plus de sens sur une forme continue (CdC ligne 737).

    Barème vide ou clé manquante → 1.0 (neutre).
    """
    if not bareme:
        return 1.0

    if forme_courbe:
        return float(bareme.get("coef_forme_courbe", 1.0))

    paliers = bareme.get("bareme_rayon", [])
    if not paliers:
        return 1.0
    for palier in paliers:
        if rayon_mm <= palier["rayon_max_mm"]:
            return float(palier["coef"])
    # Au-delà du dernier palier (rayon énorme) → plateau dernier coef
    return float(paliers[-1]["coef"])


def coef_quinconce_disposition(
    disposition: str, bareme: dict[str, Any]
) -> float:
    """Retourne le coefficient quinconce selon la disposition.

    "alignee" → 1.0 (référence). "quinconce" → coef_quinconce du barème
    (typiquement 1.10). Disposition inconnue → fallback 1.0 (sécurité).

    Barème vide → 1.0.
    """
    if not bareme:
        return 1.0
    if disposition == "quinconce":
        return float(bareme.get("coef_quinconce", 1.0))
    # alignee ou inconnue
    return 1.0
