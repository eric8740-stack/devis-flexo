"""Règle échenillage Sprint 13 S13.D.2 — SCORING + COEFS.

L'échenillage est le squelette de papier qui reste entre les étiquettes
après découpe (CdC § 505-528). C'est UNE des règles cardinales du moteur :
elle pilote à la fois la vitesse machine et la gâche matière, donc
directement le coût du devis.

Logique :
  - Intervalle dev trop faible (≤ 2-3 mm) → squelette fragile → casse
    à grande vitesse, on est forcé de ralentir.
  - Intervalle dev modéré (3-4 mm) → idéal, vitesse nominale tenable.
  - Intervalle dev grand (> 5 mm) → squelette robuste mais gâche matière
    inutile + impact vitesse paradoxal car la machine doit gérer plus
    de matière entre poses.

Le barème est paramétrable par imprimerie (table bareme.type='echenillage')
mais la courbe ICE par défaut couvre les cas standard. Une imprimerie
avec presses récentes peut adoucir le palier 5 mm (ex: vitesse 0.85 au
lieu de 0.70) ; une avec presses anciennes peut durcir.

Cette règle ne FILTRE pas — elle SCORE et applique des coefficients.
Tout intervalle dev produit un résultat exploitable.
"""
from __future__ import annotations

from typing import Any


# Palier neutre renvoyé quand le barème est vide (degraded mode).
PALIER_NEUTRE = {
    "qualite": "inconnu",
    "coef_vitesse": 1.0,
    "coef_gache": 1.0,
    "score": 0,
    "intervalle_max_mm": float("inf"),
}


def lookup_palier_echenillage(
    intervalle_dev_mm: float, bareme: list[dict[str, Any]]
) -> dict[str, Any]:
    """Renvoie le palier (qualite, coef_vitesse, coef_gache, score) qui
    correspond à un intervalle dev donné.

    Le barème est trié par `intervalle_max_mm` croissant. On prend le
    premier palier dont `intervalle_max_mm >= intervalle_dev_mm`.
    Au-delà du dernier palier (intervalle énorme), on retourne le dernier
    palier (qui est typiquement marqué "critique" avec coef_vitesse 0.40).

    Si le barème est vide → palier neutre (coefs 1.0, qualité 'inconnu',
    score 0) pour ne pas favoriser arbitrairement un cylindre.
    """
    if not bareme:
        return PALIER_NEUTRE.copy()
    for palier in bareme:
        if intervalle_dev_mm <= palier["intervalle_max_mm"]:
            return palier
    return bareme[-1]
