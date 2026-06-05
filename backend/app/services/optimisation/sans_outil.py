"""Mode « format sans outil » — géométrie d'impression pleine largeur + refente.

Lot back A. Ce module est le **2ᵉ chemin de calcul** géométrique : quand un
devis est en `mode_sans_outil`, il n'y a PAS d'outil de découpe (cylindre/
plaque). On imprime pleine largeur sur la bobine mère (laize STOCK montée),
puis on refend en bobines filles sur la finisseuse (le COÛT de refente =
lot back B, hors de ce module).

Conventions (cf. spec ETAT_PROJET « Chantier — Mode format sans outil ») :
  - `intervalle_dev = 0` (impression continue, pas d'échenillage transversal).
  - laize facturée = laize STOCK entière (déchet latéral inclus, V1).
  - déchet latéral = `laize_stock − laize_utile_refente` (tracé, jamais < 0).
  - `nb_filles` = nb de bobines filles obtenues par refente.

SACRED : ce module ne touche NI `bat_calculs` (Ø/refente = lot B) NI
`rotation_se` (8 sens). Il est purement géométrique et stateless.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GeometrieSansOutil:
    """Résultat géométrique d'un calcul « impression pleine largeur + refente ».

    Tous les champs en mm sauf `ml_total` (m) et `nb_filles` (entier).
    `laize_imprimable_mm` = largeur réellement imprimée = `min(stock, presse)`.
    `laize_utile_refente_mm` = somme des filles + intervalles de refente.
    """

    laize_stock_mm: float
    laize_imprimable_mm: float
    nb_filles: int
    intervalle_laize_mm: float
    laize_utile_refente_mm: float
    dechet_lateral_mm: float
    ml_total: float


def calculer_geometrie_sans_outil(
    laize_stock_mm: float,
    laize_utile_presse_mm: float,
    format_largeur_mm: float,
    format_hauteur_mm: float,
    intervalle_laize_mm: float,
    quantite: int,
) -> GeometrieSansOutil | None:
    """Géométrie d'une impression pleine largeur suivie d'une refente.

    On imprime sur la largeur réellement disponible = `min(laize_stock,
    laize_utile_presse)` (on ne dépasse ni la bobine mère, ni la presse),
    puis on refend en `nb_filles` colonnes d'étiquettes espacées de
    `intervalle_laize` (lames de refente).

    Returns `None` si aucune fille ne tient (format plus large que la laize
    imprimable) — le caller skippe cette machine.

    Formules :
      laize_imprimable   = min(laize_stock, laize_utile_presse)
      nb_filles          = floor((laize_imprimable + interv) / (largeur + interv))
      laize_utile_refente = nb_filles × largeur + (nb_filles − 1) × interv
      dechet_lateral     = max(0, laize_stock − laize_utile_refente)
      ml_total           = ceil(quantite × hauteur / (nb_filles × 1000))
                           (intervalle_dev = 0, impression continue)
    """
    if format_largeur_mm <= 0 or format_hauteur_mm <= 0:
        raise ValueError("format_largeur_mm et format_hauteur_mm doivent être > 0")
    if intervalle_laize_mm < 0:
        raise ValueError("intervalle_laize_mm doit être >= 0")

    laize_imprimable = min(laize_stock_mm, laize_utile_presse_mm)
    pas = format_largeur_mm + intervalle_laize_mm
    nb_filles = math.floor((laize_imprimable + intervalle_laize_mm) / pas)
    if nb_filles <= 0:
        return None

    laize_utile_refente = (
        nb_filles * format_largeur_mm + (nb_filles - 1) * intervalle_laize_mm
    )
    dechet_lateral = max(0.0, laize_stock_mm - laize_utile_refente)
    ml_total = math.ceil(quantite * format_hauteur_mm / (nb_filles * 1000))

    return GeometrieSansOutil(
        laize_stock_mm=laize_stock_mm,
        laize_imprimable_mm=laize_imprimable,
        nb_filles=nb_filles,
        intervalle_laize_mm=intervalle_laize_mm,
        laize_utile_refente_mm=laize_utile_refente,
        dechet_lateral_mm=dechet_lateral,
        ml_total=float(ml_total),
    )
