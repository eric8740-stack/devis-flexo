"""Calculs métier BAT (Bon À Tirer) — PR #9.1 FlexoCompare MVP.

Fonctions pures (pas d'I/O, pas de DB) qui dérivent, pour une
configuration de pose donnée, les valeurs nécessaires au schéma
d'implantation présenté côté UI :

  - laize_plaque    : laize physique de la plaque imprimée
  - laize_papier    : laize matière commandée chez le fournisseur
                      (laize_plaque + 2× chute latérale, arrondie au palier)
  - chute_reelle    : chute latérale effective de chaque côté
  - ml_total        : mètres linéaires totaux passant en machine
                      (avec arrondi au tour entier supérieur — métier flexo,
                      on finit toujours le tour entamé)
  - m2_consomme     : surface matière consommée (ml × laize_papier)
  - rendement       : surface utile / surface consommée (%)
  - diametre_bobine : ø physique de la bobine finie (estimation basée sur
                      épaisseur matière × ml × laize, mandrin connu)
  - laize_liner     : laize liner client (étiquette + 2× marge_liner)

Les fonctions acceptent indifféremment `float`, `int` ou `Decimal` en
entrée et renvoient le type métier le plus naturel pour l'usage UI.
"""
from __future__ import annotations

import math


def calcul_laize_plaque(
    nb_poses_laize: int,
    laize_etiq_mm: float,
    intervalle_laize_mm: float,
) -> float:
    """Largeur effective de la plaque imprimée (linéaire, pas circulaire).

    N poses produisent N−1 intervalles internes (bords libres sur la
    bobine). Formule : N × laize_etiq + (N−1) × intervalle_laize.
    """
    if nb_poses_laize <= 0:
        return 0.0
    return nb_poses_laize * laize_etiq_mm + (nb_poses_laize - 1) * intervalle_laize_mm


def calcul_laize_papier(
    laize_plaque_mm: float,
    chute_min_mm: float,
    palier_mm: int,
    laize_mini_roulable_mm: float = 0.0,
) -> float:
    """Laize matière commandée chez le fournisseur.

    La laize papier englobe la plaque ET les 2 bords latéraux (`chute_min_mm`
    par côté — l'appelant passe le **bord latéral effectif**, échenillage par
    défaut ou surcharge opérateur L1), puis on arrondit AU PALIER SUPÉRIEUR
    (les fournisseurs livrent par palier standard, typiquement 10 mm).

    L1 : plancher `laize_mini_roulable_mm` (défaut 0 → aucun plancher,
    non-régressif) : la laize papier ne descend jamais sous cette valeur
    (contrainte presse/rebobineuse).
    """
    if palier_mm <= 0:
        raise ValueError(f"palier_mm doit être > 0, reçu {palier_mm}")
    laize_mini = laize_plaque_mm + 2 * chute_min_mm
    papier = math.ceil(laize_mini / palier_mm) * palier_mm
    return max(papier, laize_mini_roulable_mm)


def calcul_chute_reelle_par_cote(
    laize_papier_mm: float,
    laize_plaque_mm: float,
) -> float:
    """Chute latérale réelle = (papier − plaque) / 2.

    Toujours ≥ chute_min_mm grâce à l'arrondi au palier supérieur dans
    `calcul_laize_papier`. Asymétrique côté gauche/droit non géré (l'algo
    flexo ICE pose la plaque centrée sur la bobine).
    """
    return (laize_papier_mm - laize_plaque_mm) / 2


def calcul_ml_total(
    quantite: int,
    nb_poses_dev: int,
    nb_poses_laize: int,
    z_cylindre_mm: float,
) -> float:
    """Mètres linéaires totaux passant en machine.

    Convention métier flexo : on finit toujours le tour entamé. Donc
    `nb_tours = ceil(quantite / nb_poses_total)`. Pour quantite=10000 et
    poses_total=8 → 1250 tours exact (pas de surplus). Pour 10001 → 1251
    tours (le tour 1251 est forcément terminé physiquement).
    """
    poses_total = nb_poses_dev * nb_poses_laize
    if poses_total <= 0:
        return 0.0
    nb_tours = math.ceil(quantite / poses_total)
    return nb_tours * z_cylindre_mm / 1000


def calcul_m2_consomme(ml_total_m: float, laize_papier_mm: float) -> float:
    """Surface matière consommée en m². ml × (laize / 1000)."""
    return ml_total_m * laize_papier_mm / 1000


def calcul_rendement(
    quantite: int,
    laize_etiq_mm: float,
    dev_etiq_mm: float,
    m2_consomme: float,
) -> float:
    """Rendement matière (%) = surface utile / surface consommée.

    Surface utile = quantite × laize_etiq × dev_etiq (en m²).
    Renvoie 0 si m2_consomme = 0 (cas dégénéré).
    """
    if m2_consomme <= 0:
        return 0.0
    m2_utiles = quantite * (laize_etiq_mm * dev_etiq_mm) / 1_000_000
    return m2_utiles / m2_consomme * 100


def calcul_diametre_bobine(
    ml_total_m: float,
    epaisseur_matiere_um: float,
    mandrin_mm: int,
    laize_papier_mm: float,
) -> int:
    """Estimation du ø de bobine fini (mm), arrondi à l'entier.

    Modèle volumique : la matière enroulée forme une couronne dont la
    section transverse (laize) × longueur (ml) × épaisseur = volume.
    Ce volume = (π × R_bobine² − π × R_mandrin²) × laize, d'où :
        R² = R_mandrin² + (épaisseur × ml × 1000) / π
    (le 1000 convertit les mètres ml en mm pour rester homogène).

    Approximation : néglige l'air entre couches (négligeable pour des
    matières fines).
    """
    if mandrin_mm <= 0 or laize_papier_mm <= 0:
        return 0
    r_mandrin_mm = mandrin_mm / 2
    epaisseur_mm = epaisseur_matiere_um / 1000
    # surface de matière enroulée vue de profil (mm²) :
    # ml_en_mm × épaisseur_mm = (ml_total_m × 1000) × epaisseur_mm
    surface_matiere_mm2 = ml_total_m * 1000 * epaisseur_mm
    r_bobine_mm = math.sqrt(r_mandrin_mm**2 + surface_matiere_mm2 / math.pi)
    return round(r_bobine_mm * 2)


def calcul_nb_max_etiq_pour_diametre(
    diametre_ext_mm: float,
    mandrin_mm: int,
    epaisseur_matiere_um: float,
    pas_mm: float,
) -> int:
    """Inverse de `calcul_diametre_bobine` côté nb étiquettes.

    Combien d'étiquettes (espacées de `pas_mm = dev_etiq + ecart_dev`)
    tiennent dans un rouleau de diamètre extérieur donné, sur mandrin
    donné, avec matière d'épaisseur donnée ? Démonstration :

        R²      = R_m² + (épaisseur_mm × ml_m × 1000) / π     (forward)
        ml_m    = nb_etiq × pas_mm / 1000
        R²      = R_m² + (épaisseur_mm × nb_etiq × pas_mm) / π
        D²      = D_m² + 4 × épaisseur_mm × nb_etiq × pas_mm / π
        nb_max  = π × (D² − D_m²) / (4 × épaisseur_mm × pas_mm)

    Mêmes hypothèses que le forward (couches jointives, air négligé).
    Garde-fous : retours à 0 si entrée incohérente (D_ext ≤ D_mandrin,
    épaisseur ou pas ≤ 0). Cohérent avec le 242 mm de la VUE B.
    """
    if mandrin_mm <= 0 or epaisseur_matiere_um <= 0 or pas_mm <= 0:
        return 0
    if diametre_ext_mm <= mandrin_mm:
        return 0
    epaisseur_mm = epaisseur_matiere_um / 1000
    # D² − D_m² peut être très grand : on garde tout en float, conversion
    # entière (floor) à la fin pour rester conservateur (« nb max physique »).
    nb_max = (
        math.pi
        * (diametre_ext_mm**2 - mandrin_mm**2)
        / (4 * epaisseur_mm * pas_mm)
    )
    return int(nb_max)


def calcul_diametre_requis_pour_nb_etiq(
    nb_etiq: int,
    mandrin_mm: int,
    epaisseur_matiere_um: float,
    pas_mm: float,
) -> int:
    """Inverse de `calcul_diametre_bobine` côté diamètre.

    Diamètre extérieur (mm) requis pour enrouler `nb_etiq` étiquettes
    de pas `pas_mm` sur mandrin donné, en matière d'épaisseur donnée.

        D_req = sqrt(D_m² + 4 × épaisseur_mm × nb_etiq × pas_mm / π)

    Mêmes hypothèses + mêmes garde-fous que `calcul_nb_max_etiq_*` ;
    arrondi à l'entier comme `calcul_diametre_bobine`.
    """
    if mandrin_mm <= 0 or epaisseur_matiere_um <= 0 or pas_mm <= 0:
        return 0
    if nb_etiq <= 0:
        return mandrin_mm
    epaisseur_mm = epaisseur_matiere_um / 1000
    d_carre = mandrin_mm**2 + 4 * epaisseur_mm * nb_etiq * pas_mm / math.pi
    return round(math.sqrt(d_carre))


def calcul_laize_liner(laize_etiq_mm: float, marge_liner_mm: float) -> float:
    """Laize du liner siliconé (chez le client, vue bobine fille).

    Le liner dépasse l'étiquette de `marge_liner_mm` de chaque côté pour
    faciliter la pose mécanique. Default ICE : 2.5 mm/côté soit liner =
    étiq + 5 mm total.
    """
    return laize_etiq_mm + 2 * marge_liner_mm
