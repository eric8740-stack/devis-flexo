"""Arbitrage pré-coupé vs découpe interne — Sprint 16 Lot B.

Compare les 2 modes d'approvisionnement mandrins :

  - **pré-coupé** : on achète N mandrins à un prix unitaire fournisseur.
    Coût = nb_bobines × prix_pre_coupe_par_mandrin_eur. Pas de coût fixe.

  - **découpe interne** : on coupe des tubes-mères à la scie de
    l'atelier. Coût = cout_fixe_decoupe_interne_eur (réglage scie,
    indépendant) + nb_bobines × cout_decoupe_interne_par_mandrin_eur
    (matière + temps unité).

Le coût fixe de découpe interne crée un seuil de bascule : au-delà d'un
certain nombre de bobines, la découpe interne devient plus économique.
Exemple : prix_pre_coupe=5 € / cout_decoupe_unitaire=2 € /
cout_fixe=39 € → seuil ≈ 13 bobines.

Si `scie_disponible=False`, le mode `decoupe_interne` est INTERDIT :
  - mode `auto` ou `pre_coupe` → applique `pre_coupe`
  - mode `decoupe_interne` forcé → lève `RebobinageError`

Si le mode forcé n'est pas le mode optimal, `motif_force` est OBLIGATOIRE
(sinon `RebobinageError`).
"""
from __future__ import annotations

from decimal import Decimal

from app.services.rebobinage.types import (
    ActionMandrin,
    ChoixOperateur,
    ParametresMandrinRuntime,
    ResultatArbitrage,
    TarifsMandrins,
)


class RebobinageError(Exception):
    """Erreur fonctionnelle du moteur rebobinage."""


def calculer_arbitrage(
    nb_bobines: int,
    tarifs: TarifsMandrins,
    parametres: ParametresMandrinRuntime,
    choix: ChoixOperateur,
) -> ResultatArbitrage:
    """Calcule les coûts des 2 modes, applique le choix opérateur.

    Args:
      nb_bobines : entier > 0, calculé par `calculer_bobines`.
      tarifs : prix pré-coupé + (coût fixe + coût unitaire découpe).
      parametres : snapshot runtime de `parametre_mandrin` (scie_disponible).
      choix : mode souhaité par l'opérateur (`auto` par défaut).

    Returns:
      ResultatArbitrage avec mode_optimal calculé, mode_applique retenu,
      coûts des 2 modes, écart relatif, motif si force.

    Raises:
      RebobinageError :
        - mode forcé `decoupe_interne` sans `scie_disponible`
        - mode forcé ≠ optimal sans motif fourni
      ValueError : nb_bobines ≤ 0 ou tarifs négatifs.
    """
    if nb_bobines <= 0:
        raise ValueError(f"nb_bobines doit être > 0 (reçu {nb_bobines})")
    if tarifs.prix_pre_coupe_par_mandrin_eur < 0:
        raise ValueError("prix_pre_coupe_par_mandrin_eur doit être ≥ 0")
    if tarifs.cout_decoupe_interne_par_mandrin_eur < 0:
        raise ValueError("cout_decoupe_interne_par_mandrin_eur doit être ≥ 0")
    if tarifs.cout_fixe_decoupe_interne_eur < 0:
        raise ValueError("cout_fixe_decoupe_interne_eur doit être ≥ 0")

    cout_pre_coupe_total = (
        Decimal(nb_bobines) * tarifs.prix_pre_coupe_par_mandrin_eur
    )
    cout_decoupe_interne_total = (
        tarifs.cout_fixe_decoupe_interne_eur
        + Decimal(nb_bobines) * tarifs.cout_decoupe_interne_par_mandrin_eur
    )

    # Mode optimal = le moins cher. Tie-breaker : pre_coupe (moins d'effort
    # opérateur, pas de réglage scie).
    if cout_decoupe_interne_total < cout_pre_coupe_total:
        mode_optimal: ActionMandrin = "decoupe_interne"
    else:
        mode_optimal = "pre_coupe"

    # Écart relatif positif (en %), borné [0, 100].
    cout_max = max(cout_pre_coupe_total, cout_decoupe_interne_total)
    if cout_max == 0:
        ecart_pct = Decimal("0")
    else:
        ecart_eur = abs(cout_pre_coupe_total - cout_decoupe_interne_total)
        ecart_pct = (ecart_eur / cout_max * Decimal(100)).quantize(
            Decimal("0.01")
        )

    # Détermine mode_applique selon choix + scie_disponible
    mode_applique, motif_force = _resoudre_mode_applique(
        mode_optimal=mode_optimal,
        choix=choix,
        scie_disponible=parametres.scie_disponible,
    )

    return ResultatArbitrage(
        mode_optimal=mode_optimal,
        cout_pre_coupe_total_eur=cout_pre_coupe_total.quantize(Decimal("0.0001")),
        cout_decoupe_interne_total_eur=cout_decoupe_interne_total.quantize(
            Decimal("0.0001")
        ),
        ecart_pct=ecart_pct,
        mode_applique=mode_applique,
        motif_force=motif_force,
    )


def _resoudre_mode_applique(
    *,
    mode_optimal: ActionMandrin,
    choix: ChoixOperateur,
    scie_disponible: bool,
) -> tuple[ActionMandrin, str | None]:
    """Détermine le mode effectivement appliqué + motif éventuel.

    Règles (priorité décroissante) :
      1. Scie indispo + `decoupe_interne` forcé → RebobinageError.
      2. Mode `auto` : applique `mode_optimal` (rétrograde vers
         pre_coupe si scie indispo).
      3. Mode forcé == optimal : applique directement, pas de motif requis.
      4. Mode forcé ≠ optimal : motif OBLIGATOIRE.
    """
    if choix.mode == "decoupe_interne" and not scie_disponible:
        raise RebobinageError(
            "Mode `decoupe_interne` forcé mais scie non disponible "
            "(parametre_mandrin.scie_disponible=False). Activez la scie "
            "ou choisissez `pre_coupe` / `auto`."
        )

    if choix.mode == "auto":
        # Rétrograde si scie absente
        if not scie_disponible and mode_optimal == "decoupe_interne":
            return ("pre_coupe", None)
        return (mode_optimal, None)

    # Mode forcé explicite (`pre_coupe` ou `decoupe_interne`)
    if choix.mode == mode_optimal:
        return (mode_optimal, None)

    # Mode forcé ≠ optimal → motif obligatoire
    if not choix.motif_force or not choix.motif_force.strip():
        raise RebobinageError(
            f"Mode `{choix.mode}` forcé alors que `{mode_optimal}` est "
            f"optimal : `motif_force` obligatoire."
        )
    return (choix.mode, choix.motif_force.strip())
