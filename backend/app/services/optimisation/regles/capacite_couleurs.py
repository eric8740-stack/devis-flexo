"""Règle capacité couleurs Sprint 13 S13.D.5 — FILTRE DUR.

CdC § 1283-1324 : à la saisie d'un devis, la machine doit avoir :

  1. Assez de groupes couleurs (stations flexo standard) pour gérer
     les couleurs d'impression (CMJN + Pantone + spot) + les options
     qui consomment des stations (vernis sélectif, back_print, etc.).

  2. Les modules spéciaux requis par chaque option sélectionnée
     (hot_stamping pour dorure à chaud, retournement_laize pour livret,
     etc.). Si un module manque, la machine est inadaptée.

Filtre dur : machine éliminée pour ce devis si capacité insuffisante
OU module manquant. L'orchestrateur exclut la machine du parc candidat.

Algorithme CdC § 1283 fidèlement repris : on vérifie d'abord les modules
(plus rapide à rejeter), puis le décompte cumulé des groupes couleurs.
"""
from __future__ import annotations

from app.services.optimisation.types import (
    FiltreResult,
    Machine,
    OptionFabrication,
)


def verifier_capacite(
    machine: Machine,
    nb_couleurs: int,
    options_selectionnees: list[OptionFabrication],
) -> FiltreResult:
    """Vérifie qu'une machine peut produire ce devis avec ses options.

    Args:
      machine : la machine candidate (nb_groupes_couleurs, options).
      nb_couleurs : nombre de couleurs d'impression demandées
        (CMJN + Pantone + spot, en stations flexo standard).
      options_selectionnees : liste des options cochées sur le devis.

    Returns:
      FiltreResult avec :
        - ok=True : la machine peut faire le job.
        - ok=False + raison='module_manquant' : il manque au moins un
          module spécial (ex: hot_stamping). Message liste le module.
        - ok=False + raison='capacite_insuffisante' : la somme des
          groupes utilisés > nb_groupes_couleurs. Message précise le
          nombre de stations en trop.
    """
    modules_disponibles = set(machine.options)

    # Étape 1 : check modules spéciaux (rejet rapide)
    for option in options_selectionnees:
        for module in option.modules_speciaux_requis:
            if module not in modules_disponibles:
                return FiltreResult(
                    ok=False,
                    raison="module_manquant",
                    message=(
                        f"Machine {machine.nom} : module '{module}' "
                        f"requis pour '{option.libelle}' non disponible "
                        f"(modules : {sorted(modules_disponibles)})."
                    ),
                )

    # Étape 2 : décompte des groupes couleurs
    groupes_utilises = nb_couleurs + sum(
        o.groupes_couleurs_requis for o in options_selectionnees
    )

    if groupes_utilises > machine.nb_groupes_couleurs:
        manquants = groupes_utilises - machine.nb_groupes_couleurs
        return FiltreResult(
            ok=False,
            raison="capacite_insuffisante",
            message=(
                f"Machine {machine.nom} : {groupes_utilises} stations "
                f"requises mais {machine.nb_groupes_couleurs} disponibles "
                f"({manquants} station(s) en trop)."
            ),
        )

    return FiltreResult(ok=True)
