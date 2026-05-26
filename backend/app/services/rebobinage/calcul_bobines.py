"""Calcul du nombre de bobines + nb étiquettes/bobine — Sprint 16 Lot B.

Règles métier :

1. Longueur enroulable sur un mandrin (mm) :
       longueur_enroulable_mm =
           π × (D_max² - D_mandrin²) / 4 / épaisseur_matière_mm

   C'est l'approximation classique pour film fin (volume section
   bobine / épaisseur). Précis à <5 % pour les épaisseurs courantes
   (35-100 µm) et les diamètres flexo standard.

2. Nb étiquettes max / bobine (entier inférieur) :
       nb_etiq_max = floor(longueur_enroulable_mm / intervalle_developpe_mm)

3. Si `nb_etiq_par_bobine_fixe` est renseigné par le profil client :
   on RESPECTE cette valeur (priorité contrat client) au lieu de
   `nb_etiq_max`. La dernière bobine peut alors être partielle.

4. Nb bobines = ceil(nb_etiquettes_total / nb_etiq_par_bobine_effectif).
   La dernière bobine peut être partielle ; on consigne
   `bobine_partielle=True` et `nb_etiq_derniere_bobine`.

5. Longueur totale matière rebobinée (m) :
       longueur_totale_m = nb_etiquettes_total × intervalle_developpe_mm / 1000
"""
from __future__ import annotations

import math
from decimal import Decimal

from app.services.rebobinage.types import ProfilClient, ResultatBobines, SpecLot


def _longueur_enroulable_mm(
    diametre_mandrin_mm: int,
    diametre_max_bobine_mm: int,
    epaisseur_matiere_mm: Decimal,
) -> Decimal:
    """Longueur de matière (mm) qui s'enroule entre D_mandrin et D_max.

    Lève ValueError si épaisseur ≤ 0 ou Dmax ≤ Dmandrin (config invalide).
    """
    if epaisseur_matiere_mm <= 0:
        raise ValueError(
            f"epaisseur_matiere_mm doit être > 0 (reçu {epaisseur_matiere_mm})"
        )
    if diametre_max_bobine_mm <= diametre_mandrin_mm:
        raise ValueError(
            f"diametre_max_bobine_mm ({diametre_max_bobine_mm}) doit être "
            f"> diametre_mandrin_mm ({diametre_mandrin_mm})"
        )

    surface_section = (
        math.pi
        * (diametre_max_bobine_mm**2 - diametre_mandrin_mm**2)
        / 4.0
    )
    longueur_float = surface_section / float(epaisseur_matiere_mm)
    return Decimal(str(longueur_float))


def calculer_bobines(
    spec: SpecLot, profil_client: ProfilClient
) -> ResultatBobines:
    """Calcule `nb_etiq_par_bobine`, `nb_bobines`, état bobine partielle.

    Args:
      spec : caractéristiques du lot (nb_etiq_total, intervalle dev, épaisseur)
      profil_client : contraintes presse aval (Dmandrin, Dmax,
        nb_etiq_par_bobine_fixe optionnel)

    Returns:
      ResultatBobines structuré.

    Raises:
      ValueError : input invalide (épaisseur ≤ 0, Dmax ≤ Dmandrin,
        intervalle ≤ 0, nb_etiq_total ≤ 0, nb_etiq_par_bobine_fixe ≤ 0).
    """
    if spec.intervalle_developpe_mm <= 0:
        raise ValueError(
            f"intervalle_developpe_mm doit être > 0 "
            f"(reçu {spec.intervalle_developpe_mm})"
        )
    if spec.nb_etiquettes_total <= 0:
        raise ValueError(
            f"nb_etiquettes_total doit être > 0 "
            f"(reçu {spec.nb_etiquettes_total})"
        )

    if profil_client.nb_etiq_par_bobine_fixe is not None:
        if profil_client.nb_etiq_par_bobine_fixe <= 0:
            raise ValueError(
                f"nb_etiq_par_bobine_fixe doit être > 0 "
                f"(reçu {profil_client.nb_etiq_par_bobine_fixe})"
            )
        nb_etiq_par_bobine = profil_client.nb_etiq_par_bobine_fixe
    else:
        long_enroulable = _longueur_enroulable_mm(
            profil_client.diametre_mandrin_mm,
            profil_client.diametre_max_bobine_mm,
            spec.epaisseur_matiere_mm,
        )
        nb_etiq_max_float = float(long_enroulable) / float(
            spec.intervalle_developpe_mm
        )
        nb_etiq_par_bobine = int(nb_etiq_max_float)  # floor (positif)
        if nb_etiq_par_bobine < 1:
            raise ValueError(
                "Capacité bobine trop faible : aucune étiquette ne tient. "
                f"Vérifier intervalle_developpe ({spec.intervalle_developpe_mm} mm) "
                f"vs Dmax ({profil_client.diametre_max_bobine_mm} mm) / "
                f"épaisseur ({spec.epaisseur_matiere_mm} mm)."
            )

    nb_bobines_complet = spec.nb_etiquettes_total // nb_etiq_par_bobine
    reste = spec.nb_etiquettes_total % nb_etiq_par_bobine

    if reste > 0:
        nb_bobines = nb_bobines_complet + 1
        bobine_partielle = True
        nb_etiq_derniere_bobine = reste
    else:
        nb_bobines = nb_bobines_complet
        bobine_partielle = False
        nb_etiq_derniere_bobine = nb_etiq_par_bobine

    longueur_totale_m = (
        Decimal(spec.nb_etiquettes_total)
        * spec.intervalle_developpe_mm
        / Decimal(1000)
    )

    return ResultatBobines(
        nb_etiq_par_bobine=nb_etiq_par_bobine,
        nb_bobines=nb_bobines,
        bobine_partielle=bobine_partielle,
        nb_etiq_derniere_bobine=nb_etiq_derniere_bobine,
        longueur_totale_m=longueur_totale_m,
    )
