"""Orchestrateur du moteur d'optimisation Sprint 13 Lot S13.D.7a.

Implémente l'algorithme principal `optimiser_pose()` qui :
  1. Applique la contrainte client (S13.D.6) pour figer l'intervalle dev min.
  2. Filtre les machines par capacité couleurs + modules (S13.D.5).
  3. Pour chaque (cylindre × machine survivantes × variante de poses laize) :
     - Calcule nb_poses_dev (S13.D.2 implicite via floor)
     - Filtre l'effet banane (S13.D.1)
     - Cumule les coefficients (S13.D.2/3/4 + options)
     - Calcule coût machine + score
  4. Trie par score DESC, retourne le top 3 (CdC § 658 'pas de triche').

Convention CdC § 658 : si moins de 3 candidats viables, on retourne moins
de 3 — on ne dégrade JAMAIS les contraintes pour faire du remplissage.

Hors scope de cette implémentation (Sprint 14+) :
  - Spot détection verso automatique pour matières transparentes
    (sera ajouté comme option auto-cochée par le router avant appel moteur)
  - Cout matière (besoin du prix au m² de la matière sélectionnée)
  - Test automatique des 2 dispositions alignée vs quinconce (l'imprimeur
    bascule manuellement via UI)
"""
from __future__ import annotations

import math

from app.services.optimisation.regles.capacite_couleurs import (
    verifier_capacite,
)
from app.services.optimisation.regles.compensation_laize_dev import (
    evaluer_compensation,
)
from app.services.optimisation.regles.confort_roulage import (
    coef_confort_rayon,
    coef_quinconce_disposition,
)
from app.services.optimisation.regles.contrainte_client import (
    intervalle_dev_min_effectif,
)
from app.services.optimisation.regles.echenillage import (
    lookup_palier_echenillage,
)
from app.services.optimisation.regles.effet_banane import (
    lookup_developpe_mini,
    valide_effet_banane,
)
from app.services.optimisation.types import (
    ConfigurationPose,
    Machine,
    OptimisationInput,
    OptimisationOutput,
)


def _calcul_nb_poses_dev(
    developpe_mm: float, hauteur_mm: float, intervalle_min_mm: float
) -> tuple[int, float] | None:
    """Calcule (nb_poses_dev, intervalle_dev_reel_mm) pour un cylindre.

    Algo CdC § 595 : on tente d'abord le `floor`, puis si l'intervalle
    dev résultant est sous le minimum, on réduit nb_poses_dev de 1 et
    on recalcule. Si nb_poses_dev devient 0 → impossible, on retourne None.
    """
    pas = hauteur_mm + intervalle_min_mm
    nb_poses = math.floor(developpe_mm / pas)
    if nb_poses == 0:
        return None
    intervalle = developpe_mm / nb_poses - hauteur_mm
    if intervalle < intervalle_min_mm:
        nb_poses -= 1
        if nb_poses == 0:
            return None
        intervalle = developpe_mm / nb_poses - hauteur_mm
    return nb_poses, intervalle


# CdC § 661 : intervalle laize MAX = 5 mm en pratique standard flexo.
# Au-delà, ce n'est plus un intervalle utile, c'est de la matière perdue
# inutilement. On cap donc l'intervalle laize à 5 mm et on accepte des
# "bords perdus" sur la bobine — pas la plaque qui fait toute la laize.
INTERVALLE_LAIZE_MAX_MM = 5.0


def _calcul_intervalle_laize(
    laize_utile: float, format_largeur: float, variante: int
) -> float | None:
    """Intervalle laize réel entre poses pour une variante.

    Returns:
      None si variante n'est pas faisable (poses ne rentrent pas dans
      la laize). 0 si variante=1 (une seule pose). Sinon
      min((laize_utile - variante × largeur) / (variante - 1),
          INTERVALLE_LAIZE_MAX_MM).
    """
    espace_dispo = laize_utile - variante * format_largeur
    if espace_dispo < 0:
        return None
    if variante <= 1:
        return 0.0
    intervalle_brut = espace_dispo / (variante - 1)
    return min(intervalle_brut, INTERVALLE_LAIZE_MAX_MM)


def _calcul_largeur_plaque(
    format_largeur: float, variante: int, intervalle_laize: float
) -> float:
    """Largeur effective de la plaque (CdC § 617)."""
    return variante * format_largeur + (variante - 1) * intervalle_laize


def _produit_options_coef_vitesse(options) -> float:
    coef = 1.0
    for o in options:
        coef *= o.coef_vitesse_impact
    return coef


def _produit_options_coef_gache(options) -> float:
    coef = 1.0
    for o in options:
        coef *= o.coef_gache_impact
    return coef


def _calcul_score(config: ConfigurationPose, palier_score: float) -> float:
    """Score [0..200ish] : base palier échenillage × (vitesse / gâche).

    Formule simple :
      score = palier_score × coef_vitesse_final / coef_gache_final

    Justification : à palier échenillage égal, une config plus rapide ET
    moins gâcheuse mérite un meilleur score. Le ratio cumule les bonus
    confort_rayon, consolidation, quinconce, options. Pas de borne dure
    (un quinconce + confort 5mm + consolidation peut dépasser 100).
    """
    if config.coef_gache_final == 0:
        return 0.0
    return palier_score * config.coef_vitesse_final / config.coef_gache_final


def _dedoublonner_configs(
    candidats: list[ConfigurationPose],
) -> list[ConfigurationPose]:
    """Fusionne les configs ne différant que par la machine.

    PR #9.1 : deux configs avec mêmes (cylindre, nb_poses_dev,
    nb_poses_laize, intervalles dev/laize) mais des machines différentes
    sont métier-équivalentes — c'est juste un choix machine. On garde la
    config avec le meilleur score (déjà en tête après tri) et on agrège
    les machine_id alternatifs dans `machines_compatibles`.

    L'entrée DOIT être triée par score DESC (pour que la première config
    rencontrée pour chaque clé soit la meilleure).
    """
    def cle(c: ConfigurationPose) -> tuple:
        return (
            c.cylindre_id,
            c.nb_poses_dev,
            c.nb_poses_laize,
            round(c.intervalle_dev_reel_mm, 3),
            round(c.intervalle_laize_reel_mm, 3),
        )

    fusionne: dict[tuple, ConfigurationPose] = {}
    for c in candidats:
        k = cle(c)
        if k in fusionne:
            # Ajout du machine_id de la config dupliquée à la représentative.
            for mid in c.machines_compatibles:
                if mid not in fusionne[k].machines_compatibles:
                    fusionne[k].machines_compatibles.append(mid)
        else:
            fusionne[k] = c
    return list(fusionne.values())


def _filtre_machines_par_capacite(
    machines: list[Machine],
    nb_couleurs: int,
    options,
) -> list[tuple[Machine, str | None]]:
    """Retourne la liste des (machine, raison_exclusion=None) viables
    + (machine, raison) pour les exclues (pour message_filtrage final).
    """
    viables: list[tuple[Machine, str | None]] = []
    for m in machines:
        res = verifier_capacite(m, nb_couleurs, options)
        if res.ok:
            viables.append((m, None))
        else:
            viables.append((m, res.raison))
    return viables


def optimiser_pose(inp: OptimisationInput) -> OptimisationOutput:
    """Fonction principale du moteur d'optimisation.

    Voir docstring du module pour la séquence détaillée des règles.
    """
    # 1. Contrainte client → intervalle dev min applique
    cc = intervalle_dev_min_effectif(
        intervalle_min_imprimeur=inp.intervalle_dev_min_mm,
        intervalle_min_client=inp.contrainte_client.intervalle_dev_min_mm,
    )
    intervalle_min = cc["intervalle_dev_min_applique_mm"]

    # 2. Filtre machines par capacité couleurs (calculé une fois par machine)
    machines_viables = [
        m
        for (m, raison) in _filtre_machines_par_capacite(
            inp.machines, inp.nb_couleurs_impression, inp.options
        )
        if raison is None
    ]

    # Coefficients liés aux options (constants pour tout candidat)
    coef_v_options = _produit_options_coef_vitesse(inp.options)
    coef_g_options = _produit_options_coef_gache(inp.options)

    # 3. Boucles imbriquées
    candidats: list[ConfigurationPose] = []

    for cyl in inp.cylindres:
        res_dev = _calcul_nb_poses_dev(
            developpe_mm=cyl.developpe_mm,
            hauteur_mm=inp.format.hauteur_mm,
            intervalle_min_mm=intervalle_min,
        )
        if res_dev is None:
            continue
        nb_poses_dev, intervalle_dev_reel = res_dev

        palier_echen = lookup_palier_echenillage(
            intervalle_dev_reel, inp.bareme_echenillage
        )

        for machine in machines_viables:
            nb_poses_laize_max = math.floor(
                (machine.laize_utile_mm + intervalle_min)
                / (inp.format.largeur_mm + intervalle_min)
            )
            if nb_poses_laize_max == 0:
                continue

            # Adaptation de l'algo CdC § 613 ("max, max-1, max-2") :
            # quand l'effet banane exclut les variantes les plus larges
            # (plaque trop grande pour ce cylindre), on descend jusqu'à
            # trouver la première variante utilisable. Puis on teste
            # celle-ci + 2 inférieures (pour avoir des alternatives à
            # arbitrer). Cap pratique : variante ≥ 1.
            variante_top: int | None = None
            for v in range(nb_poses_laize_max, 0, -1):
                il = _calcul_intervalle_laize(
                    machine.laize_utile_mm, inp.format.largeur_mm, v
                )
                if il is None:
                    continue
                lp = _calcul_largeur_plaque(inp.format.largeur_mm, v, il)
                z = lookup_developpe_mini(lp, inp.bareme_effet_banane)
                if cyl.developpe_mm >= z:
                    variante_top = v
                    break
            if variante_top is None:
                continue  # aucune variante laize ne passe l'effet banane

            for delta in (0, 1, 2):
                variante = variante_top - delta
                if variante <= 0:
                    continue
                intervalle_laize = _calcul_intervalle_laize(
                    laize_utile=machine.laize_utile_mm,
                    format_largeur=inp.format.largeur_mm,
                    variante=variante,
                )
                if intervalle_laize is None:
                    continue

                largeur_plaque = _calcul_largeur_plaque(
                    inp.format.largeur_mm, variante, intervalle_laize
                )

                # Filtre dur effet banane (et capture du Z mini pour audit)
                z_mini = lookup_developpe_mini(
                    largeur_plaque, inp.bareme_effet_banane
                )
                fb = valide_effet_banane(
                    cyl, largeur_plaque, inp.bareme_effet_banane
                )
                if not fb.ok:
                    continue

                # Compensation (bonus optionnel)
                comp = evaluer_compensation(
                    intervalle_dev_reel,
                    intervalle_laize,
                    inp.bareme_compensation,
                )

                # Confort de roulage (rayon + quinconce alignée par défaut)
                coef_rayon = coef_confort_rayon(
                    inp.format.rayon_angles_mm,
                    inp.format.forme_courbe,
                    inp.bareme_confort_roulage,
                )
                coef_quinconce = coef_quinconce_disposition(
                    "alignee", inp.bareme_confort_roulage
                )

                # Cumul coef vitesse échenillage : si consolidation atteinte,
                # le coef vitesse est remplacé par coef_vitesse_si_atteint.
                coef_v_echen = palier_echen["coef_vitesse"]
                if comp["consolidation_atteinte"]:
                    coef_v_echen = comp["coef_vitesse_si_atteint"]

                config = ConfigurationPose(
                    cylindre_id=cyl.id,
                    machine_id=machine.id,
                    nb_poses_dev=nb_poses_dev,
                    nb_poses_laize=variante,
                    nb_poses_total=nb_poses_dev * variante,
                    intervalle_dev_reel_mm=round(intervalle_dev_reel, 2),
                    intervalle_laize_reel_mm=round(intervalle_laize, 2),
                    largeur_plaque_mm=round(largeur_plaque, 2),
                    z_mini_effet_banane=z_mini,
                    coef_vitesse_echenillage=coef_v_echen,
                    coef_gache_echenillage=palier_echen["coef_gache"],
                    coef_confort_rayon=coef_rayon,
                    coef_quinconce=coef_quinconce,
                    coef_consolidation=1.0,  # déjà absorbé dans coef_v_echen
                    coef_vitesse_options=coef_v_options,
                    coef_gache_options=coef_g_options,
                    qualite_echenillage=palier_echen["qualite"],
                    consolidation_atteinte=comp["consolidation_atteinte"],
                    intervalle_laize_souhaitable_mm=comp[
                        "intervalle_laize_souhaitable_mm"
                    ],
                    disposition_poses="alignee",
                )

                config.score = _calcul_score(config, palier_echen["score"])
                config.machines_compatibles = [machine.id]

                candidats.append(config)

    # 4. Tri + dédoublonnage + top 3
    candidats.sort(key=lambda c: c.score, reverse=True)
    candidats = _dedoublonner_configs(candidats)
    top = candidats[:3]
    nb = len(top)

    message: str | None = None
    if nb < 3:
        message = (
            "Effet banane, capacité couleurs et contraintes parc machine "
            f"ont éliminé certaines options. {nb} configuration(s) "
            f"viable(s) trouvée(s)."
        )

    return OptimisationOutput(
        configurations=top,
        nb_candidats=nb,
        message_filtrage=message,
        intervalle_dev_min_applique_mm=intervalle_min,
        message_contrainte_client=cc["message"],
    )
