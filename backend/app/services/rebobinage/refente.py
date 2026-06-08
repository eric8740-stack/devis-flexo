"""Coût de refente / rebobinage — lot back B (ADDITIF au devis).

Le module rebobinage Sprint-16 (`calcul_bobines` + `calcul_temps`) calcule
l'**axe longueur (Ø)** : pour UNE bande, combien de bobines filles le long du
développé (jusqu'au Ø max) et le temps machine. La refente « mode sans outil »
AJOUTE l'**axe largeur** : la laize imprimée est refendue en `nb_filles` bandes
parallèles. Les deux axes sont ORTHOGONAUX :

    nb_bobines_clients_total = nb_filles × nb_bobines_par_fille (axe Ø)

`nb_filles` MULTIPLIE le temps machine, le nb de raccords ET la gâche — il ne
les écrase pas. La source de `nb_filles` est la valeur RÉSOLUE de lot back A
(géométrie + `nb_filles_force`), JAMAIS `nb_poses_laize`.

Coût refente (config-driven, tenant) :
    temps_refente_h = (Σ temps machine filles + temps gâche) / 60
    cout = temps_refente_h × ConfigCouts.cout_exploitation_rebobineuse_eur_h
avec gâche raccord = ConfigCouts.gache_raccord_pct × longueur rebobinée
(valorisée au même taux machine, V1 simple — cf. spec « corrigeable »).

ADDITIF : ce coût n'entre PAS dans `prix_vente_ht` (7 postes figés) — il est
porté par `ht_total` (canal rebobinage existant). `bat_calculs` / `rotation_se`
INTOUCHÉS ; la géométrie Ø est réutilisée via `calculer_bobines`.

**Pas de poste fantôme** : si `nb_filles <= 1` (pas de refente réelle), la ligne
est `applicable=False` et le coût est 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services.rebobinage.types import ResultatBobines


@dataclass(frozen=True)
class ResultatRefente:
    """Résultat du chiffrage refente d'un lot (additif)."""

    applicable: bool
    nb_filles: int
    nb_bobines_par_fille: int
    nb_bobines_total: int
    longueur_rebobinee_m: Decimal
    gache_metres: Decimal
    temps_refente_h: Decimal
    cout_refente_eur: Decimal


def calculer_cout_refente(
    *,
    nb_filles: int,
    longueur_par_fille_m: Decimal,
    bobines_par_fille: ResultatBobines,
    vitesse_pratique_m_min: int,
    temps_changement_bobine_min: Decimal,
    cout_exploitation_rebobineuse_eur_h: Decimal,
    gache_raccord_pct: Decimal,
) -> ResultatRefente:
    """Coût de refente (axe largeur × nb_filles) + gâche raccord.

    Args:
      nb_filles : nb de bandes de refente RÉSOLU (lot back A). <= 1 → pas de
        refente (ligne non applicable, coût 0).
      longueur_par_fille_m : longueur de bande rebobinée par fille (= ml total
        machine, chaque fille parcourt toute la longueur imprimée).
      bobines_par_fille : sortie `calculer_bobines` pour UNE fille (axe Ø).
      vitesse_pratique_m_min / temps_changement_bobine_min : params rebobineuse.
      cout_exploitation_rebobineuse_eur_h : taux horaire refente (ConfigCouts).
      gache_raccord_pct : % de gâche au raccord (ConfigCouts).

    Returns:
      ResultatRefente. `applicable=False` + coût 0 si `nb_filles <= 1`.

    Raises:
      ValueError si vitesse <= 0 ou taux/gâche < 0.
    """
    if vitesse_pratique_m_min <= 0:
        raise ValueError(
            f"vitesse_pratique_m_min doit être > 0 (reçu {vitesse_pratique_m_min})"
        )
    if cout_exploitation_rebobineuse_eur_h < 0:
        raise ValueError("cout_exploitation_rebobineuse_eur_h doit être >= 0")
    if gache_raccord_pct < 0:
        raise ValueError("gache_raccord_pct doit être >= 0")

    # Pas de refente réelle (1 seule fille, pas de slitting) → pas de poste
    # fantôme : ligne non applicable, coût 0.
    if nb_filles <= 1:
        return ResultatRefente(
            applicable=False,
            nb_filles=max(nb_filles, 0),
            nb_bobines_par_fille=bobines_par_fille.nb_bobines,
            nb_bobines_total=max(nb_filles, 0) * bobines_par_fille.nb_bobines,
            longueur_rebobinee_m=Decimal("0"),
            gache_metres=Decimal("0"),
            temps_refente_h=Decimal("0"),
            cout_refente_eur=Decimal("0.00"),
        )

    nb_f = Decimal(nb_filles)
    vitesse = Decimal(vitesse_pratique_m_min)

    # Axe longueur (par fille) : roulage + changements de bobines (raccords).
    temps_roulage_fille_min = longueur_par_fille_m / vitesse
    nb_changements_fille = max(0, bobines_par_fille.nb_bobines - 1)
    temps_changements_fille_min = (
        Decimal(nb_changements_fille) * temps_changement_bobine_min
    )
    temps_fille_min = temps_roulage_fille_min + temps_changements_fille_min

    # Axe largeur : nb_filles MULTIPLIE le temps machine ET les raccords.
    temps_machine_min = nb_f * temps_fille_min

    # Gâche raccord : % de la longueur rebobinée totale (toutes filles), perdue
    # aux raccords → temps machine équivalent (valorisée au taux refente, V1).
    longueur_rebobinee_m = nb_f * longueur_par_fille_m
    gache_metres = (gache_raccord_pct / Decimal(100)) * longueur_rebobinee_m
    temps_gache_min = gache_metres / vitesse

    temps_refente_min = temps_machine_min + temps_gache_min
    temps_refente_h = temps_refente_min / Decimal(60)
    cout = (temps_refente_h * cout_exploitation_rebobineuse_eur_h).quantize(
        Decimal("0.01")
    )

    return ResultatRefente(
        applicable=True,
        nb_filles=nb_filles,
        nb_bobines_par_fille=bobines_par_fille.nb_bobines,
        nb_bobines_total=nb_filles * bobines_par_fille.nb_bobines,
        longueur_rebobinee_m=longueur_rebobinee_m.quantize(Decimal("0.01")),
        gache_metres=gache_metres.quantize(Decimal("0.01")),
        temps_refente_h=temps_refente_h.quantize(Decimal("0.0001")),
        cout_refente_eur=cout,
    )
