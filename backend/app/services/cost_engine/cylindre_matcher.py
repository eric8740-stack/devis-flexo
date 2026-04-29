"""Sprint 7 V2 — Matching cylindres magnétiques (mode 'matching').

Formule métier corrigée par tableau Excel `Develop.xlsx` Eric (28 ans flexo
ICE) — la circonférence du cylindre se divise en N étiquettes par tour :

    pas_mm = (Z × DENT_MM) / nb_etiq_par_tour
    intervalle_mm = pas_mm - format_h

Le moteur cherche les meilleurs **couples (Z, nb_etiq_par_tour)** dans
les plages réelles flexo (Z=51..144, nb_etiq=1..40) qui satisfont 3
contraintes simultanées :
  - Hauteur : 2.5 ≤ intervalle_mm ≤ 15
  - Largeur effet banane : Z ≥ Z_mini selon table empirique abaque
  - Laize machine : largeur_plaque ≤ laize_max - 2 × marge sécurité 5 mm

Stratégie : on garde **1 candidat par Z** (le couple qui donne le meilleur
intervalle pour ce cylindre physique). Tri final par intervalle croissant
(= meilleur prix au mille en premier). Top 3 retournés.

Pas de table SQL pour l'abaque effet banane — constante Python lookup
direct (table empirique non-linéaire avec saut Z=120→160 entre 250-300 mm).
"""
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from app.models import Machine
from app.services.cost_engine.errors import CostEngineError

# ---------------------------------------------------------------------------
# Constantes métier (validées par tableau Develop.xlsx Eric)
# ---------------------------------------------------------------------------

DENT_MM = Decimal("3.175")  # 1 dent = 1/8 pouce (convention industrielle flexo)

# Plage Z corrigée v2 (vraie plage flexo ICE, pas 72-187 du brief v1)
Z_MIN = 51   # circonférence ~161.93 mm
Z_MAX = 144  # circonférence ~457.20 mm

# Plage nb_etiq_par_tour (1 à 40, limite haute du tableau Eric)
NB_ETIQ_MIN = 1
NB_ETIQ_MAX = 40

# Contrainte hauteur métier (intervalle entre étiquettes, sens longitudinal)
INTERVALLE_MIN = Decimal("2.5")
INTERVALLE_MAX = Decimal("15.0")

# Marge sécurité largeur plaque vs laize machine (Sprint 7 décision Eric :
# défaut conservateur 5 mm de chaque côté = 10 mm total). À durcir Sprint 8
# si retours terrain demandent une marge paramétrable par machine.
MARGE_SECURITE_LAIZE_MM = Decimal("5")

# Table empirique effet banane (mémoire Eric ICE 28 ans, 6 paliers).
# LOOKUP DIRECT — table non-linéaire, saut Z=120→160 entre 250-300 mm.
# Note : palier 350 → Z=160 dépasse Z_MAX=144 → erreur 422 attendue
# pour les plaques > 300 mm (parc standard insuffisant).
TABLE_EFFET_BANANE: list[tuple[Decimal, int]] = [
    (Decimal("150"), 80),
    (Decimal("200"), 96),
    (Decimal("250"), 104),
    (Decimal("300"), 120),
    (Decimal("350"), 160),
    # > 350 → 160 (lookup default)
]


# ---------------------------------------------------------------------------
# Helper interne (non exposé Pydantic — l'orchestrator mappe vers
# CandidatCylindreOutput en y ajoutant le devis HT calculé)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidatCylindre:
    """Représentation interne d'un cylindre candidat (couple Z, nb_etiq)."""

    z: int
    nb_etiq_par_tour: int
    circonference_mm: Decimal
    pas_mm: Decimal
    intervalle_mm: Decimal
    nb_etiq_par_metre: int


# ---------------------------------------------------------------------------
# Logique métier
# ---------------------------------------------------------------------------


def lookup_z_mini_banane(largeur_plaque_mm: Decimal) -> int:
    """Retourne le Z mini requis selon la table empirique effet banane.

    Plus la plaque est large, plus elle doit être tendue sur un grand
    cylindre pour limiter l'effet banane (déformation latérale).
    """
    for seuil, z_mini in TABLE_EFFET_BANANE:
        if largeur_plaque_mm <= seuil:
            return z_mini
    return 160  # > 350 mm : ré-utilise le palier max


def find_cylindre_candidats(
    format_h_mm: int,
    largeur_plaque_mm: Decimal,
    machine: Machine,
) -> list[CandidatCylindre]:
    """Cherche les couples (Z, nb_etiq_par_tour) compatibles, retourne top 3.

    Algorithme :
      1. Filtre laize machine (court-circuit erreur 422 immédiate)
      2. Lookup Z_mini effet banane (selon largeur_plaque)
      3. Boucle imbriquée Z × nb_etiq, garder 1 candidat par Z (meilleur intervalle)
      4. Tri intervalle croissant + top 3

    Args:
        format_h_mm: hauteur étiquette (sens longitudinal défilement)
        largeur_plaque_mm: largeur totale plaque polymère = format_l × nb_poses_l
        machine: objet Machine SQLAlchemy avec laize_max_mm renseigné

    Raises:
        CostEngineError 422 si plaque trop large OU aucun couple compatible.
    """
    # Filtre 1 : laize machine
    largeur_max_admissible = machine.laize_max_mm - 2 * MARGE_SECURITE_LAIZE_MM
    if largeur_plaque_mm > largeur_max_admissible:
        raise CostEngineError(
            f"Plaque {largeur_plaque_mm} mm > laize {machine.laize_max_mm} mm "
            f"de la machine '{machine.nom}' (marge sécurité 2 × "
            f"{MARGE_SECURITE_LAIZE_MM} mm). Largeur max admissible : "
            f"{largeur_max_admissible} mm."
        )

    # Filtre 2 : effet banane (Z mini global pour cette largeur)
    z_mini_banane = lookup_z_mini_banane(largeur_plaque_mm)

    # Boucle imbriquée Z × nb_etiq_par_tour — 1 candidat par Z (meilleur intervalle)
    candidats_par_z: dict[int, CandidatCylindre] = {}
    format_h_dec = Decimal(format_h_mm)
    for z in range(Z_MIN, Z_MAX + 1):
        if z < z_mini_banane:
            continue
        circonference = Decimal(z) * DENT_MM
        for nb_etiq in range(NB_ETIQ_MIN, NB_ETIQ_MAX + 1):
            pas_mm = circonference / Decimal(nb_etiq)
            intervalle = pas_mm - format_h_dec
            if intervalle < INTERVALLE_MIN or intervalle > INTERVALLE_MAX:
                continue
            # nb_etiq_par_metre = floor(1000 / pas_mm)
            nb_etiq_par_metre = int(
                (Decimal(1000) / pas_mm).to_integral_value(rounding=ROUND_DOWN)
            )
            cand = CandidatCylindre(
                z=z,
                nb_etiq_par_tour=nb_etiq,
                circonference_mm=circonference,
                pas_mm=pas_mm,
                intervalle_mm=intervalle,
                nb_etiq_par_metre=nb_etiq_par_metre,
            )
            # Garder le meilleur intervalle pour ce Z (1 candidat par cylindre)
            if (
                z not in candidats_par_z
                or intervalle < candidats_par_z[z].intervalle_mm
            ):
                candidats_par_z[z] = cand

    if not candidats_par_z:
        raise CostEngineError(
            f"Aucun cylindre magnétique compatible (plage Z={Z_MIN}..{Z_MAX} × "
            f"nb_etiq={NB_ETIQ_MIN}..{NB_ETIQ_MAX}, intervalle "
            f"{INTERVALLE_MIN}-{INTERVALLE_MAX} mm, effet banane Z>={z_mini_banane} "
            f"pour plaque {largeur_plaque_mm} mm). Combinaison hauteur/largeur "
            "hors plage standard. Devis sur demande après étude technique."
        )

    # Tri par intervalle croissant (= meilleur prix au mille en premier)
    candidats = sorted(candidats_par_z.values(), key=lambda c: c.intervalle_mm)

    # Top 3 (ou moins si moins de candidats compatibles)
    return candidats[:3]
