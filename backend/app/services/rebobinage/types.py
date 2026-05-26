"""Types d'entrée/sortie du moteur rebobinage — Sprint 16 Lot B.

Dataclasses immutables (frozen=True) pour expliciter le contrat. Toutes
les valeurs financières sont en `Decimal` pour préserver la précision ;
les compteurs (nb_etiquettes, nb_bobines, etc.) restent en `int`.

Le profil client (`diametre_mandrin_mm`, `diametre_max_bobine_mm`,
`nb_etiq_par_bobine_fixe`) est passé en RUNTIME — l'extension `client`
en BDD est reportée à un commit ultérieur (cf. note Lot A
`q1f3a5d7e9c2`). Cela permet d'avancer le moteur sans dépendance DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal


ModeRebobinage = Literal["auto", "pre_coupe", "decoupe_interne"]
ActionMandrin = Literal["pre_coupe", "decoupe_interne"]


@dataclass(frozen=True)
class SpecLot:
    """Caractéristiques de la production à rebobiner."""

    # Quantité totale d'étiquettes à produire.
    nb_etiquettes_total: int
    # Pas inter-étiquette dans le sens développé (= circonférence cyl
    # divisée par nb_poses_dev en flexo). Une "longueur d'étiquette"
    # côté bobine = ce pas, car les étiquettes se suivent en continu.
    intervalle_developpe_mm: Decimal
    # Épaisseur de la matière imprimée (mm). Sert au calcul de longueur
    # enroulable selon Dmax. Pour les complexes multi-couches, c'est
    # l'épaisseur totale de la bande.
    epaisseur_matiere_mm: Decimal


@dataclass(frozen=True)
class ProfilClient:
    """Contraintes presse-aval du client (passées en runtime au moteur)."""

    diametre_mandrin_mm: int
    diametre_max_bobine_mm: int
    # Optionnel : si renseigné, le client veut exactement N étiquettes par
    # bobine (la dernière peut être partielle, géré par le moteur).
    nb_etiq_par_bobine_fixe: int | None = None


@dataclass(frozen=True)
class MachineRebobinageParams:
    """Paramètres d'une rebobineuse pour ce job."""

    # Vitesse RÉELLE saisie par l'imprimeur (pas constructeur).
    vitesse_pratique_m_min: int
    cout_horaire_eur: Decimal
    # Temps de changement de bobine (entre 2 bobines successives).
    temps_changement_bobine_min: Decimal


@dataclass(frozen=True)
class TarifsMandrins:
    """Tarifs des 2 modes d'approvisionnement mandrins.

    `cout_fixe_decoupe_interne_eur` est le surcoût FIXE de réglage scie
    (indépendant du nb de mandrins) — crée le seuil de bascule entre les
    2 modes. Sans ce coût fixe, le mode optimal serait linéairement
    déterminé par la différence des prix à l'unité, sans inflexion.
    """

    prix_pre_coupe_par_mandrin_eur: Decimal
    cout_decoupe_interne_par_mandrin_eur: Decimal
    cout_fixe_decoupe_interne_eur: Decimal = Decimal("0")


@dataclass(frozen=True)
class ParametresMandrinRuntime:
    """Snapshot runtime de `parametre_mandrin` de l'entreprise.

    `scie_disponible=False` interdit le mode `decoupe_interne` (le
    moteur force `pre_coupe` même en `auto` ou lève une erreur en mode
    forcé `decoupe_interne`).
    """

    scie_disponible: bool
    mode_par_defaut: ModeRebobinage = "auto"


@dataclass(frozen=True)
class ChoixOperateur:
    """Choix mode opérateur pour ce job.

    `mode="auto"` → moteur applique le mode optimal.
    `mode="pre_coupe"` ou `"decoupe_interne"` → force le choix. Si le
    mode forcé n'est PAS le mode optimal calculé, `motif_force` est
    OBLIGATOIRE (sinon `RebobinageError`). Le motif est consigné dans
    le résultat pour traçabilité.
    """

    mode: ModeRebobinage = "auto"
    motif_force: str | None = None


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultatBobines:
    nb_etiq_par_bobine: int
    nb_bobines: int
    bobine_partielle: bool
    nb_etiq_derniere_bobine: int
    longueur_totale_m: Decimal


@dataclass(frozen=True)
class ResultatTemps:
    temps_roulage_min: Decimal
    temps_changements_min: Decimal
    temps_total_min: Decimal
    cout_machine_eur: Decimal


@dataclass(frozen=True)
class ResultatArbitrage:
    """Verdict de l'arbitrage pre_coupe vs decoupe_interne.

    `mode_optimal` = le mode économiquement le plus avantageux (calculé).
    `mode_applique` = le mode effectivement retenu (= optimal si auto et
    scie OK, sinon ce que l'opérateur a forcé).
    `ecart_pct` = écart relatif entre les 2 coûts, positif (en %).
    `motif_force` = motif fourni par l'opérateur si mode forcé ≠ optimal.
    """

    mode_optimal: ActionMandrin
    cout_pre_coupe_total_eur: Decimal
    cout_decoupe_interne_total_eur: Decimal
    ecart_pct: Decimal
    mode_applique: ActionMandrin
    motif_force: str | None


@dataclass(frozen=True)
class ResultatRebobinage:
    bobines: ResultatBobines
    temps: ResultatTemps
    arbitrage: ResultatArbitrage
    cout_mandrins_eur: Decimal  # selon mode_applique
    cout_total_rebobinage_eur: Decimal  # cout_machine + cout_mandrins
