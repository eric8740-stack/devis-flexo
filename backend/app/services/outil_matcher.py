"""Service Sprint 14 Lot 2 — matching outil de découpe.

Propose au commercial les cylindres magnétiques compatibles avec un brief
client (laize + dev étiquette + intervalles + laize machine). Quand aucun
cylindre du parc ne convient, propose l'option « fabriquer un nouvel
outil sur mesure » avec un coût hardcodé (200 €) pour le MVP — Lot 4 le
branchera sur `tarif_poste` réel.

Service STATELESS : pas de session DB. Le router scope `entreprise_id` et
hydrate la liste `cylindres_disponibles` depuis CylindreMagnetique avant
d'appeler `matcher_outils()`. Ce découplage garantit qu'`outil_matcher`
reste testable hors-web et indépendant de toute logique sacred du package
`app.services.cost_engine`.

Constantes métier (PAS_CHENILLE_MM=3.175, COUT_NOUVEL_OUTIL=200) volontairement
DUPLIQUÉES depuis cylindre_matcher.py (sacred) pour éviter une dépendance
inverse vers le package cost_engine. Si la valeur change un jour côté
sacred, c'est un événement métier qu'on synchronise manuellement ici.
"""
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from typing import Iterable

from app.models import CylindreMagnetique


# ---------------------------------------------------------------------------
# Constantes métier
# ---------------------------------------------------------------------------


# 1 dent = 1/8 pouce = 3,175 mm (convention industrielle flexo). Même
# valeur que cylindre_matcher.DENT_MM (sacred) — duplication assumée pour
# l'indépendance du service.
PAS_CHENILLE_MM_DEFAULT = Decimal("3.175")


# Coût hardcoded MVP pour l'option « nouvel outil à fabriquer ». TODO Lot 4 :
# brancher sur la lecture de `tarif_poste` (poste P3 outillage) pour que
# chaque tenant ajuste son barème.
COUT_NOUVEL_OUTIL_EUR_DEFAUT = Decimal("200")


# ---------------------------------------------------------------------------
# Dataclasses publiques (contrat API stable validé Sprint 14 §3 Lot 2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContrainteOutil:
    """Contraintes métier issues du brief client unifié.

    Toutes les dimensions sont en mm. Le service ne fait pas d'hypothèse sur
    l'unité de la `laize_machine_mm` (elle vient du modèle Machine côté
    router) — il l'utilise telle quelle pour le filtre dur.
    """

    laize_etiquette_mm: Decimal
    dev_etiquette_mm: Decimal
    intervalle_dev_mm: Decimal
    intervalle_laize_mm: Decimal
    laize_machine_mm: Decimal
    nb_fronts_min: int = 1
    nb_fronts_max: int = 10


@dataclass(frozen=True)
class MatchOutil:
    """Un match candidat — cylindre existant (id rempli) ou option fabriquer."""

    cylindre_id: int | None
    nb_dents: int
    developpe_mm: Decimal
    nb_poses_dev: int
    nb_poses_laize: int
    nb_poses_total: int
    cout_outil_eur: Decimal
    score_efficacite: float


# ---------------------------------------------------------------------------
# Logique interne
# ---------------------------------------------------------------------------


def _calculer_nb_poses_dev(developpe_mm: Decimal, pas_dev_mm: Decimal) -> int:
    """floor(developpe / pas_dev), 0 si pas_dev > developpe."""
    if pas_dev_mm <= 0 or developpe_mm < pas_dev_mm:
        return 0
    return int(developpe_mm / pas_dev_mm)


def _calculer_score(
    nb_poses_dev: int,
    nb_poses_laize: int,
    laize_etiq: Decimal,
    dev_etiq: Decimal,
    developpe_mm: Decimal,
    laize_machine_mm: Decimal,
) -> float:
    """Score = surface_étiquettes / surface_développée_machine (∈ ]0, 1]).

    Métrique de % de matière effectivement utilisée par les étiquettes
    parmi la matière qui passe sous le cylindre à chaque tour. Plus c'est
    haut, mieux on amortit le tour cylindre.
    """
    surface_utile = (
        Decimal(nb_poses_dev) * Decimal(nb_poses_laize) * laize_etiq * dev_etiq
    )
    surface_developpee = developpe_mm * laize_machine_mm
    if surface_developpee <= 0:
        return 0.0
    return float(surface_utile / surface_developpee)


def _meilleur_match_pour_cylindre(
    cyl: CylindreMagnetique,
    contrainte: ContrainteOutil,
    pas_dev_mm: Decimal,
    pas_laize_mm: Decimal,
    nb_fronts_min: int,
    nb_fronts_max: int,
    pas_chenille_mm: Decimal,
) -> MatchOutil | None:
    """Calcule le meilleur (nb_poses_laize) pour ce cylindre, ou None si
    aucune combinaison ne respecte les contraintes."""
    nb_poses_dev = _calculer_nb_poses_dev(cyl.developpe_mm, pas_dev_mm)
    if nb_poses_dev == 0:
        return None

    nb_dents = int(cyl.developpe_mm / pas_chenille_mm)
    best: MatchOutil | None = None
    for nb_fronts in range(nb_fronts_min, nb_fronts_max + 1):
        score = _calculer_score(
            nb_poses_dev,
            nb_fronts,
            contrainte.laize_etiquette_mm,
            contrainte.dev_etiquette_mm,
            cyl.developpe_mm,
            contrainte.laize_machine_mm,
        )
        if best is None or score > best.score_efficacite:
            best = MatchOutil(
                cylindre_id=cyl.id,
                nb_dents=nb_dents,
                developpe_mm=cyl.developpe_mm,
                nb_poses_dev=nb_poses_dev,
                nb_poses_laize=nb_fronts,
                nb_poses_total=nb_poses_dev * nb_fronts,
                cout_outil_eur=Decimal(0),
                score_efficacite=score,
            )
    return best


def _construire_option_nouvel_outil(
    contrainte: ContrainteOutil,
    pas_chenille_mm: Decimal,
    cout_nouvel_outil_eur: Decimal,
    nb_fronts_effectif: int,
) -> MatchOutil:
    """Dimensionne un cylindre fictif juste-assez pour 1 pose dev minimum.

    Calcule le nb_dents minimum tel que developpe ≥ pas_dev, donc le
    cylindre le plus petit possible compatible avec l'étiquette.
    """
    pas_dev = contrainte.dev_etiquette_mm + contrainte.intervalle_dev_mm
    # nb_dents = ceil(pas_dev / pas_chenille) — au moins 1 pose dev
    nb_dents = int(
        (pas_dev / pas_chenille_mm).to_integral_value(rounding=ROUND_CEILING)
    )
    nb_dents = max(nb_dents, 1)
    developpe = pas_chenille_mm * Decimal(nb_dents)
    nb_poses_dev = max(1, _calculer_nb_poses_dev(developpe, pas_dev))
    score = _calculer_score(
        nb_poses_dev,
        nb_fronts_effectif,
        contrainte.laize_etiquette_mm,
        contrainte.dev_etiquette_mm,
        developpe,
        contrainte.laize_machine_mm,
    )
    return MatchOutil(
        cylindre_id=None,
        nb_dents=nb_dents,
        developpe_mm=developpe,
        nb_poses_dev=nb_poses_dev,
        nb_poses_laize=nb_fronts_effectif,
        nb_poses_total=nb_poses_dev * nb_fronts_effectif,
        cout_outil_eur=cout_nouvel_outil_eur,
        score_efficacite=score,
    )


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------


def matcher_outils(
    contrainte: ContrainteOutil,
    cylindres_disponibles: Iterable[CylindreMagnetique],
    pas_chenille_mm: Decimal = PAS_CHENILLE_MM_DEFAULT,
    cout_nouvel_outil_eur: Decimal = COUT_NOUVEL_OUTIL_EUR_DEFAUT,
) -> list[MatchOutil]:
    """Retourne les outils compatibles, triés par score d'efficacité DESC.

    Algorithme :
      1. Calcule pas_dev / pas_laize / borne nb_fronts (intersection contrainte
         × capacité machine).
      2. Pour chaque cylindre actif fourni, calcule le meilleur (nb_poses_laize)
         et retient un match — 1 candidat par cylindre.
      3. Si aucun cylindre n'a produit de match (étiquette trop grande pour
         le parc), propose une option unique « fabriquer un nouvel outil ».
      4. Tri par score décroissant et retourne la liste complète (le router
         ou l'UI peuvent tronquer à top N selon contexte).

    Args:
        contrainte: brief client (étiquette + intervalles + laize machine).
        cylindres_disponibles: itérable de CylindreMagnetique (scopés tenant
            par le router, déjà filtrés actif=True idéalement).
        pas_chenille_mm: pas chenille standard flexo (default 3,175 mm).
        cout_nouvel_outil_eur: coût hardcoded de l'option fabriquer (default
            200 € — TODO Lot 4 : lookup tarif_poste).

    Returns:
        list[MatchOutil] non vide :
        - 1+ matches existants triés par score DESC, OU
        - Exactement 1 option `cylindre_id=None` si aucun existant compatible.
    """
    pas_dev = contrainte.dev_etiquette_mm + contrainte.intervalle_dev_mm
    pas_laize = contrainte.laize_etiquette_mm + contrainte.intervalle_laize_mm

    # Borne nb_fronts = intersection contrainte utilisateur × capacité machine
    nb_fronts_min = max(1, contrainte.nb_fronts_min)
    nb_fronts_max_machine = (
        int(contrainte.laize_machine_mm / pas_laize) if pas_laize > 0 else 0
    )
    nb_fronts_max = min(contrainte.nb_fronts_max, nb_fronts_max_machine)

    # Si même 1 front ne tient pas dans la laize machine → directement
    # nouvel outil (avec nb_fronts forcé à 1 pour rester cohérent).
    if nb_fronts_max < nb_fronts_min:
        return [
            _construire_option_nouvel_outil(
                contrainte, pas_chenille_mm, cout_nouvel_outil_eur, 1
            )
        ]

    matches: list[MatchOutil] = []
    for cyl in cylindres_disponibles:
        if not cyl.actif:
            continue
        best = _meilleur_match_pour_cylindre(
            cyl,
            contrainte,
            pas_dev,
            pas_laize,
            nb_fronts_min,
            nb_fronts_max,
            pas_chenille_mm,
        )
        if best is not None:
            matches.append(best)

    if not matches:
        # Aucun cylindre existant ne convient → option fabriquer, dimensionnée
        # pour 1 pose dev × nb_fronts_max (ou nb_fronts_min à défaut).
        nb_fronts_effectif = max(1, nb_fronts_max if nb_fronts_max >= 1 else nb_fronts_min)
        return [
            _construire_option_nouvel_outil(
                contrainte,
                pas_chenille_mm,
                cout_nouvel_outil_eur,
                nb_fronts_effectif,
            )
        ]

    matches.sort(key=lambda m: m.score_efficacite, reverse=True)
    return matches
