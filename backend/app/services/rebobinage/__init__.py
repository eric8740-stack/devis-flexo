"""Module de calcul rebobinage — Sprint 16 Lot B.

Service ISOLÉ, distinct de `cost_engine/`. Le coût rebobinage est une
ligne ADDITIVE dans le devis (cf. Lot C — pas encore implémenté).
**SACRED INVARIANT** : aucune modification ni dépendance vers
`cost_engine` ; les valeurs sacrées V1a/V1b/V7a restent intactes.

Entry point public : `calculer_rebobinage(spec, profil_client, machine,
tarifs, parametres, choix) → ResultatRebobinage`. Voir `moteur.py`.
"""
from app.services.rebobinage.moteur import (
    RebobinageError,
    calculer_rebobinage,
)
from app.services.rebobinage.types import (
    ChoixOperateur,
    MachineRebobinageParams,
    ModeRebobinage,
    ParametresMandrinRuntime,
    ProfilClient,
    ResultatArbitrage,
    ResultatBobines,
    ResultatRebobinage,
    ResultatTemps,
    SpecLot,
    TarifsMandrins,
)

__all__ = [
    "calculer_rebobinage",
    "RebobinageError",
    "SpecLot",
    "ProfilClient",
    "MachineRebobinageParams",
    "TarifsMandrins",
    "ParametresMandrinRuntime",
    "ChoixOperateur",
    "ModeRebobinage",
    "ResultatBobines",
    "ResultatTemps",
    "ResultatArbitrage",
    "ResultatRebobinage",
]
