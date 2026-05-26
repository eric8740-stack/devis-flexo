"""Moteur de calcul rebobinage — point d'entrée Sprint 16 Lot B.

Orchestre les 3 sous-modules :
  1. `calcul_bobines` → nb bobines + nb étiq/bobine + longueur totale
  2. `calcul_temps` → temps + coût machine
  3. `arbitrage_mandrins` → mode mandrins optimal/appliqué + coûts

Retourne un `ResultatRebobinage` complet, additif au cost_engine (qui
reste sacré et intouché). Le Lot C consommera ce résultat pour intégrer
la ligne « Rebobinage » au devis.
"""
from __future__ import annotations

from decimal import Decimal

from app.services.rebobinage.arbitrage_mandrins import (
    RebobinageError,
    calculer_arbitrage,
)
from app.services.rebobinage.calcul_bobines import calculer_bobines
from app.services.rebobinage.calcul_temps import calculer_temps_et_cout_machine
from app.services.rebobinage.types import (
    ChoixOperateur,
    MachineRebobinageParams,
    ParametresMandrinRuntime,
    ProfilClient,
    ResultatRebobinage,
    SpecLot,
    TarifsMandrins,
)


def calculer_rebobinage(
    *,
    spec: SpecLot,
    profil_client: ProfilClient,
    machine: MachineRebobinageParams,
    tarifs: TarifsMandrins,
    parametres: ParametresMandrinRuntime,
    choix: ChoixOperateur | None = None,
) -> ResultatRebobinage:
    """Calcule le résultat rebobinage complet (bobines + temps + coût).

    Args:
      spec : caractéristiques du lot à rebobiner.
      profil_client : contraintes presse-aval (Dmandrin, Dmax, nb_etiq fixe).
      machine : params rebobineuse choisie.
      tarifs : prix mandrins (pré-coupé + découpe interne).
      parametres : snapshot runtime de `parametre_mandrin`.
      choix : mode opérateur (defaults à `auto`).

    Returns:
      ResultatRebobinage : agrégat des 3 sous-résultats + total.

    Raises:
      ValueError : input invalide (cf. sous-modules).
      RebobinageError : conflit mode forcé / contraintes (cf. arbitrage).
    """
    if choix is None:
        choix = ChoixOperateur(mode="auto")

    # 1. Bobines
    bobines = calculer_bobines(spec, profil_client)

    # 2. Temps + coût machine
    temps = calculer_temps_et_cout_machine(bobines, machine)

    # 3. Arbitrage mandrins
    arbitrage = calculer_arbitrage(
        nb_bobines=bobines.nb_bobines,
        tarifs=tarifs,
        parametres=parametres,
        choix=choix,
    )

    # Coût mandrins selon le mode effectivement appliqué
    if arbitrage.mode_applique == "pre_coupe":
        cout_mandrins_eur = arbitrage.cout_pre_coupe_total_eur
    else:
        cout_mandrins_eur = arbitrage.cout_decoupe_interne_total_eur

    cout_total_rebobinage_eur = (
        temps.cout_machine_eur + cout_mandrins_eur
    ).quantize(Decimal("0.0001"))

    return ResultatRebobinage(
        bobines=bobines,
        temps=temps,
        arbitrage=arbitrage,
        cout_mandrins_eur=cout_mandrins_eur,
        cout_total_rebobinage_eur=cout_total_rebobinage_eur,
    )
