"""Tests TDD du moteur rebobinage — Sprint 16 Lot B.

Couvre toutes les règles du brief avec ≥ 2 tests par règle :

  1. Calcul nb bobines selon Dmax / intervalle / épaisseur
  2. Bobine partielle gérée (reste > 0)
  3. nb_etiq_par_bobine_fixe respecté (priorité contrat client)
  4. Temps = roulage + changements (changement entre bobines uniquement)
  5. Coût machine = temps × cout_horaire
  6. Arbitrage pre_coupe vs decoupe_interne (seuil de bascule)
  7. scie_disponible=False interdit decoupe_interne
  8. Mode forcé sans motif → erreur ; avec motif → applique

Test du seuil ~13 bobines (réf CdC, mandrin 76/Dmax 226mm) couvert dans
les tests de l'arbitrage.

Calculs ISOLÉS du cost_engine — aucune valeur sacrée (V1a/V1b/V7a) ne
peut être affectée par ce moteur.
"""
from decimal import Decimal

import pytest

from app.services.rebobinage import (
    ChoixOperateur,
    MachineRebobinageParams,
    ParametresMandrinRuntime,
    ProfilClient,
    RebobinageError,
    SpecLot,
    TarifsMandrins,
    calculer_rebobinage,
)
from app.services.rebobinage.arbitrage_mandrins import calculer_arbitrage
from app.services.rebobinage.calcul_bobines import calculer_bobines
from app.services.rebobinage.calcul_temps import calculer_temps_et_cout_machine


# ---------------------------------------------------------------------------
# Helpers — fabriques d'inputs réalistes (cas étiquettes flexo standard)
# ---------------------------------------------------------------------------


def _spec_standard(nb_etiq: int = 10000) -> SpecLot:
    return SpecLot(
        nb_etiquettes_total=nb_etiq,
        intervalle_developpe_mm=Decimal("80"),  # 80 mm d'écart entre étiqs
        epaisseur_matiere_mm=Decimal("0.06"),  # 60 µm typique étiquette
    )


def _profil_standard(
    nb_etiq_fixe: int | None = None,
) -> ProfilClient:
    return ProfilClient(
        diametre_mandrin_mm=76,
        diametre_max_bobine_mm=226,
        nb_etiq_par_bobine_fixe=nb_etiq_fixe,
    )


def _machine_standard() -> MachineRebobinageParams:
    return MachineRebobinageParams(
        vitesse_pratique_m_min=80,
        cout_horaire_eur=Decimal("45.00"),
        temps_changement_bobine_min=Decimal("1.50"),
    )


def _tarifs_seuil_13(
    cout_fixe: Decimal = Decimal("39"),
    prix_pre_coupe: Decimal = Decimal("5"),
    cout_decoupe_unitaire: Decimal = Decimal("2"),
) -> TarifsMandrins:
    """Tarifs callés sur un seuil de bascule à 13 bobines.

    À 13 bobines : pre_coupe = 13×5 = 65 € ; decoupe = 39 + 13×2 = 65 €.
    En dessous de 13 → pre_coupe optimal ; au-dessus → decoupe_interne.
    """
    return TarifsMandrins(
        prix_pre_coupe_par_mandrin_eur=prix_pre_coupe,
        cout_decoupe_interne_par_mandrin_eur=cout_decoupe_unitaire,
        cout_fixe_decoupe_interne_eur=cout_fixe,
    )


def _params_avec_scie() -> ParametresMandrinRuntime:
    return ParametresMandrinRuntime(scie_disponible=True, mode_par_defaut="auto")


def _params_sans_scie() -> ParametresMandrinRuntime:
    return ParametresMandrinRuntime(scie_disponible=False, mode_par_defaut="auto")


# ---------------------------------------------------------------------------
# Règle 1 — Calcul nb bobines (Dmax, intervalle, épaisseur)
# ---------------------------------------------------------------------------


def test_calcul_bobines_capacite_normale():
    """Pour mandrin 76 / Dmax 226 / épaisseur 60 µm / intervalle 80 mm :
    longueur enroulable ≈ π × (226² - 76²) / 4 / 0.06 ≈ 592 530 mm,
    nb_etiq_par_bobine ≈ 592 530 / 80 ≈ 7406 étiquettes."""
    spec = _spec_standard(nb_etiq=10000)
    profil = _profil_standard()
    res = calculer_bobines(spec, profil)
    # Tolérance large (la formule est une approximation film fin).
    assert 7000 <= res.nb_etiq_par_bobine <= 7800
    # 10 000 / ~7400 ≈ 1 bobine complète + reste = 2 bobines
    assert res.nb_bobines == 2
    assert res.bobine_partielle is True
    assert res.nb_etiq_derniere_bobine == 10000 - res.nb_etiq_par_bobine
    # Longueur totale = 10000 × 80 mm / 1000 = 800 m
    assert res.longueur_totale_m == Decimal("800.000")


def test_calcul_bobines_petite_serie_une_seule_bobine():
    """Petite série : 1000 étiquettes < capacité d'une bobine → 1 bobine
    partielle, pas de changement."""
    spec = _spec_standard(nb_etiq=1000)
    res = calculer_bobines(spec, _profil_standard())
    assert res.nb_bobines == 1
    assert res.bobine_partielle is True
    assert res.nb_etiq_derniere_bobine == 1000


def test_calcul_bobines_input_invalides_levent_value_error():
    """Inputs aberrants → ValueError (épaisseur ≤ 0, Dmax ≤ Dmandrin,
    intervalle ≤ 0, nb_etiq_total ≤ 0)."""
    profil = _profil_standard()
    with pytest.raises(ValueError, match="epaisseur"):
        calculer_bobines(
            SpecLot(10000, Decimal("80"), Decimal("0")), profil
        )
    with pytest.raises(ValueError, match="diametre"):
        calculer_bobines(
            _spec_standard(),
            ProfilClient(diametre_mandrin_mm=300, diametre_max_bobine_mm=200),
        )
    with pytest.raises(ValueError, match="intervalle"):
        calculer_bobines(
            SpecLot(10000, Decimal("0"), Decimal("0.06")), profil
        )
    with pytest.raises(ValueError, match="nb_etiquettes_total"):
        calculer_bobines(
            SpecLot(0, Decimal("80"), Decimal("0.06")), profil
        )


# ---------------------------------------------------------------------------
# Règle 2 — Bobine partielle (reste > 0)
# ---------------------------------------------------------------------------


def test_bobine_partielle_quand_reste_strictement_positif():
    """nb_etiq fixe à 1000, total 2500 → 2 complètes + 1 partielle (500)."""
    spec = _spec_standard(nb_etiq=2500)
    profil = _profil_standard(nb_etiq_fixe=1000)
    res = calculer_bobines(spec, profil)
    assert res.nb_bobines == 3
    assert res.bobine_partielle is True
    assert res.nb_etiq_derniere_bobine == 500


def test_pas_de_bobine_partielle_quand_diviseur_exact():
    """nb_etiq fixe 1000, total 5000 → 5 bobines pleines, pas de partielle."""
    spec = _spec_standard(nb_etiq=5000)
    profil = _profil_standard(nb_etiq_fixe=1000)
    res = calculer_bobines(spec, profil)
    assert res.nb_bobines == 5
    assert res.bobine_partielle is False
    assert res.nb_etiq_derniere_bobine == 1000


# ---------------------------------------------------------------------------
# Règle 3 — nb_etiq_par_bobine_fixe respecté (priorité contrat client)
# ---------------------------------------------------------------------------


def test_nb_etiq_fixe_respecte_meme_si_capacite_superieure():
    """Le client veut 500 étiqs par bobine, la capacité physique permet
    7000+ → on RESPECTE 500 (priorité contrat client). 10 000 étiqs →
    20 bobines pleines."""
    spec = _spec_standard(nb_etiq=10000)
    profil = _profil_standard(nb_etiq_fixe=500)
    res = calculer_bobines(spec, profil)
    assert res.nb_etiq_par_bobine == 500
    assert res.nb_bobines == 20
    assert res.bobine_partielle is False


def test_nb_etiq_fixe_zero_ou_negatif_leve_value_error():
    spec = _spec_standard()
    with pytest.raises(ValueError, match="nb_etiq_par_bobine_fixe"):
        calculer_bobines(spec, _profil_standard(nb_etiq_fixe=0))
    with pytest.raises(ValueError, match="nb_etiq_par_bobine_fixe"):
        calculer_bobines(spec, _profil_standard(nb_etiq_fixe=-5))


# ---------------------------------------------------------------------------
# Règle 4 — Temps = roulage + (nb_bobines - 1) × temps_changement
# ---------------------------------------------------------------------------


def test_temps_une_seule_bobine_pas_de_changement():
    """Avec 1 bobine, le temps_changements doit être 0 (changement
    compte ENTRE bobines, pas après la dernière)."""
    spec = _spec_standard(nb_etiq=1000)  # longueur 80 m
    bobines = calculer_bobines(spec, _profil_standard())
    assert bobines.nb_bobines == 1
    temps = calculer_temps_et_cout_machine(bobines, _machine_standard())
    # Roulage = 80 m / 80 m/min = 1 min
    assert temps.temps_roulage_min == Decimal("1.0000")
    assert temps.temps_changements_min == Decimal("0.0000")
    assert temps.temps_total_min == Decimal("1.0000")


def test_temps_n_bobines_inclut_n_moins_1_changements():
    """Avec 4 bobines (donc 3 changements à 1.5 min) + 800 m à 80 m/min
    → 10 min roulage + 4.5 min changements = 14.5 min."""
    spec = _spec_standard(nb_etiq=10000)  # longueur 800 m
    profil = _profil_standard(nb_etiq_fixe=2500)  # 4 bobines pleines
    bobines = calculer_bobines(spec, profil)
    assert bobines.nb_bobines == 4
    temps = calculer_temps_et_cout_machine(bobines, _machine_standard())
    assert temps.temps_roulage_min == Decimal("10.0000")
    assert temps.temps_changements_min == Decimal("4.5000")
    assert temps.temps_total_min == Decimal("14.5000")


# ---------------------------------------------------------------------------
# Règle 5 — Coût machine = temps × cout_horaire
# ---------------------------------------------------------------------------


def test_cout_machine_simple():
    """14.5 min à 45 €/h = 14.5 × 45 / 60 = 10.875 €."""
    spec = _spec_standard(nb_etiq=10000)
    profil = _profil_standard(nb_etiq_fixe=2500)
    bobines = calculer_bobines(spec, profil)
    temps = calculer_temps_et_cout_machine(bobines, _machine_standard())
    assert temps.cout_machine_eur == Decimal("10.8750")


def test_cout_machine_zero_si_vitesse_max_et_pas_changements():
    """1 bobine, vitesse extrêmement rapide → coût ≈ 0."""
    spec = _spec_standard(nb_etiq=80)  # 6.4 m, 1 bobine
    machine = MachineRebobinageParams(
        vitesse_pratique_m_min=1000,
        cout_horaire_eur=Decimal("60.00"),
        temps_changement_bobine_min=Decimal("0"),
    )
    bobines = calculer_bobines(spec, _profil_standard())
    temps = calculer_temps_et_cout_machine(bobines, machine)
    # 6.4 m / 1000 m/min = 0.0064 min × 60 €/h / 60 = 0.0064 €
    assert temps.cout_machine_eur == Decimal("0.0064")


# ---------------------------------------------------------------------------
# Règle 6 — Arbitrage pre_coupe vs decoupe_interne, seuil de bascule
# ---------------------------------------------------------------------------


def test_arbitrage_12_bobines_pre_coupe_reste_optimal():
    """Seuil callé à 13 bobines (39 € fixe / 5 €-2 € unit). À 12 →
    pre_coupe (60 €) < decoupe (39 + 24 = 63 €)."""
    arb = calculer_arbitrage(
        nb_bobines=12,
        tarifs=_tarifs_seuil_13(),
        parametres=_params_avec_scie(),
        choix=ChoixOperateur(mode="auto"),
    )
    assert arb.mode_optimal == "pre_coupe"
    assert arb.mode_applique == "pre_coupe"
    assert arb.cout_pre_coupe_total_eur == Decimal("60.0000")
    assert arb.cout_decoupe_interne_total_eur == Decimal("63.0000")
    assert arb.motif_force is None


def test_arbitrage_14_bobines_decoupe_devient_optimale():
    """À 14 bobines : pre_coupe = 70 €, decoupe = 39 + 28 = 67 € →
    decoupe_interne optimal."""
    arb = calculer_arbitrage(
        nb_bobines=14,
        tarifs=_tarifs_seuil_13(),
        parametres=_params_avec_scie(),
        choix=ChoixOperateur(mode="auto"),
    )
    assert arb.mode_optimal == "decoupe_interne"
    assert arb.mode_applique == "decoupe_interne"
    assert arb.cout_pre_coupe_total_eur == Decimal("70.0000")
    assert arb.cout_decoupe_interne_total_eur == Decimal("67.0000")
    # Écart relatif : 3 / 70 × 100 ≈ 4.29 %
    assert arb.ecart_pct == Decimal("4.29")


def test_arbitrage_seuil_exact_13_egalite_tie_breaker_pre_coupe():
    """À 13 bobines : pre_coupe = 65, decoupe = 39 + 26 = 65 → égalité.
    Tie-breaker = pre_coupe (moins d'effort opérateur, pas de réglage)."""
    arb = calculer_arbitrage(
        nb_bobines=13,
        tarifs=_tarifs_seuil_13(),
        parametres=_params_avec_scie(),
        choix=ChoixOperateur(mode="auto"),
    )
    assert arb.mode_optimal == "pre_coupe"
    assert arb.cout_pre_coupe_total_eur == arb.cout_decoupe_interne_total_eur
    assert arb.ecart_pct == Decimal("0.00")


# ---------------------------------------------------------------------------
# Règle 7 — scie_disponible=False interdit decoupe_interne
# ---------------------------------------------------------------------------


def test_scie_indispo_mode_auto_retrograde_vers_pre_coupe():
    """À 14 bobines (decoupe_interne serait optimal) mais scie indispo →
    auto retombe sur pre_coupe sans erreur."""
    arb = calculer_arbitrage(
        nb_bobines=14,
        tarifs=_tarifs_seuil_13(),
        parametres=_params_sans_scie(),
        choix=ChoixOperateur(mode="auto"),
    )
    assert arb.mode_optimal == "decoupe_interne"  # le calcul reste exact
    assert arb.mode_applique == "pre_coupe"  # rétrogradation
    assert arb.motif_force is None


def test_scie_indispo_mode_decoupe_force_leve_erreur():
    """Mode forcé `decoupe_interne` sans scie → RebobinageError explicite."""
    with pytest.raises(RebobinageError, match="scie"):
        calculer_arbitrage(
            nb_bobines=14,
            tarifs=_tarifs_seuil_13(),
            parametres=_params_sans_scie(),
            choix=ChoixOperateur(
                mode="decoupe_interne", motif_force="test"
            ),
        )


# ---------------------------------------------------------------------------
# Règle 8 — Mode forcé : motif obligatoire si != optimal
# ---------------------------------------------------------------------------


def test_mode_force_egal_a_optimal_pas_de_motif_requis():
    """Si l'opérateur force le mode déjà optimal, pas besoin de motif."""
    arb = calculer_arbitrage(
        nb_bobines=14,
        tarifs=_tarifs_seuil_13(),
        parametres=_params_avec_scie(),
        choix=ChoixOperateur(mode="decoupe_interne", motif_force=None),
    )
    assert arb.mode_applique == "decoupe_interne"
    assert arb.motif_force is None  # force == optimal, pas remonté


def test_mode_force_different_de_optimal_sans_motif_leve_erreur():
    """Force `pre_coupe` alors que `decoupe_interne` est optimal, sans
    motif → erreur."""
    with pytest.raises(RebobinageError, match="motif_force"):
        calculer_arbitrage(
            nb_bobines=14,
            tarifs=_tarifs_seuil_13(),
            parametres=_params_avec_scie(),
            choix=ChoixOperateur(mode="pre_coupe", motif_force=None),
        )


def test_mode_force_different_avec_motif_applique_et_consigne():
    """Force `pre_coupe` ≠ optimal, motif fourni → applique + consigné."""
    arb = calculer_arbitrage(
        nb_bobines=14,
        tarifs=_tarifs_seuil_13(),
        parametres=_params_avec_scie(),
        choix=ChoixOperateur(
            mode="pre_coupe",
            motif_force="Demande explicite client : pas de découpe interne",
        ),
    )
    assert arb.mode_optimal == "decoupe_interne"
    assert arb.mode_applique == "pre_coupe"
    assert arb.motif_force == (
        "Demande explicite client : pas de découpe interne"
    )


def test_mode_force_motif_vide_blanc_traite_comme_manquant():
    """Motif="   " (whitespace only) → traité comme absent → erreur."""
    with pytest.raises(RebobinageError, match="motif_force"):
        calculer_arbitrage(
            nb_bobines=14,
            tarifs=_tarifs_seuil_13(),
            parametres=_params_avec_scie(),
            choix=ChoixOperateur(mode="pre_coupe", motif_force="   "),
        )


# ---------------------------------------------------------------------------
# Moteur orchestrateur — E2E intégration
# ---------------------------------------------------------------------------


def test_moteur_e2e_cas_typique_auto():
    """Pipeline complet : 10 000 étiqs, 2500 par bobine fixe, 4 bobines,
    14 bobines → decoupe_interne, calcul cohérent end-to-end."""
    res = calculer_rebobinage(
        spec=_spec_standard(nb_etiq=10000),
        profil_client=_profil_standard(nb_etiq_fixe=2500),
        machine=_machine_standard(),
        tarifs=_tarifs_seuil_13(),
        parametres=_params_avec_scie(),
        choix=ChoixOperateur(mode="auto"),
    )
    # 4 bobines (10 000 / 2500)
    assert res.bobines.nb_bobines == 4
    # 4 bobines < seuil 13 → pre_coupe optimal (coûts 20 € vs 39+8=47 €)
    assert res.arbitrage.mode_optimal == "pre_coupe"
    assert res.arbitrage.mode_applique == "pre_coupe"
    # cout_mandrins reflète le mode appliqué
    assert res.cout_mandrins_eur == res.arbitrage.cout_pre_coupe_total_eur
    # cout total = cout_machine + cout_mandrins
    assert res.cout_total_rebobinage_eur == (
        res.temps.cout_machine_eur + res.cout_mandrins_eur
    )


def test_moteur_e2e_grosse_serie_bascule_decoupe():
    """Grosse série : 50 000 étiqs, 1000 par bobine → 50 bobines → bien
    au-delà du seuil 13 → decoupe_interne optimal et appliqué."""
    res = calculer_rebobinage(
        spec=_spec_standard(nb_etiq=50000),
        profil_client=_profil_standard(nb_etiq_fixe=1000),
        machine=_machine_standard(),
        tarifs=_tarifs_seuil_13(),
        parametres=_params_avec_scie(),
    )
    assert res.bobines.nb_bobines == 50
    assert res.arbitrage.mode_optimal == "decoupe_interne"
    assert res.arbitrage.mode_applique == "decoupe_interne"
    # decoupe = 39 + 50×2 = 139 € ; pre_coupe = 250 € ; écart 44.4 %
    assert res.arbitrage.cout_decoupe_interne_total_eur == Decimal("139.0000")
    assert res.arbitrage.cout_pre_coupe_total_eur == Decimal("250.0000")
    assert res.arbitrage.ecart_pct == Decimal("44.40")
    assert res.cout_mandrins_eur == Decimal("139.0000")
