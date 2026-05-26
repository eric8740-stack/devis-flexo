"""Calcul du temps de rebobinage + coût machine — Sprint 16 Lot B.

Règles métier :

1. Temps de roulage = longueur_totale_m / vitesse_pratique_m_min (min)
2. Temps de changements entre bobines = (nb_bobines - 1) ×
   temps_changement_bobine_min. Le changement compte ENTRE bobines, pas
   après la dernière → 0 si une seule bobine.
3. Temps total = roulage + changements (min)
4. Coût machine = temps_total / 60 × cout_horaire_eur (€)
"""
from __future__ import annotations

from decimal import Decimal

from app.services.rebobinage.types import (
    MachineRebobinageParams,
    ResultatBobines,
    ResultatTemps,
)


def calculer_temps_et_cout_machine(
    bobines: ResultatBobines, machine: MachineRebobinageParams
) -> ResultatTemps:
    """Temps de rebobinage + coût machine.

    Args:
      bobines : sortie de `calculer_bobines` (longueur totale + nb bobines).
      machine : params rebobineuse (vitesse, coût horaire, temps changement).

    Returns:
      ResultatTemps (roulage, changements, total, coût machine).

    Raises:
      ValueError si vitesse_pratique_m_min ≤ 0 ou cout_horaire_eur < 0.
    """
    if machine.vitesse_pratique_m_min <= 0:
        raise ValueError(
            f"vitesse_pratique_m_min doit être > 0 "
            f"(reçu {machine.vitesse_pratique_m_min})"
        )
    if machine.cout_horaire_eur < 0:
        raise ValueError(
            f"cout_horaire_eur doit être ≥ 0 "
            f"(reçu {machine.cout_horaire_eur})"
        )

    temps_roulage_min = bobines.longueur_totale_m / Decimal(
        machine.vitesse_pratique_m_min
    )
    nb_changements = max(0, bobines.nb_bobines - 1)
    temps_changements_min = (
        Decimal(nb_changements) * machine.temps_changement_bobine_min
    )
    temps_total_min = temps_roulage_min + temps_changements_min

    cout_machine_eur = (
        temps_total_min / Decimal(60) * machine.cout_horaire_eur
    )

    # Arrondi à 4 décimales pour cohérence avec les autres montants
    # financiers du projet (Numeric(*, 4)).
    return ResultatTemps(
        temps_roulage_min=temps_roulage_min.quantize(Decimal("0.0001")),
        temps_changements_min=temps_changements_min.quantize(Decimal("0.0001")),
        temps_total_min=temps_total_min.quantize(Decimal("0.0001")),
        cout_machine_eur=cout_machine_eur.quantize(Decimal("0.0001")),
    )
