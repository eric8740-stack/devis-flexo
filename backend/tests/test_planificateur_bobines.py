"""Tests — planificateur de bobines (3 scénarios + IMPOSE anti-fléau).

Brief Eric : « Tests : 3 scénarios sur cas type (Q=10000, n_laize=3,
Ø200→~3000) · surprod · Ø cohérents helper · coût via cost_engine ·
cas Q indivisible. »

Cas type calculé à la main :
  Q = 10000, n_laize = 3   → R = ceil(10000/3) = 3334
  pas = 80 mm, mandrin = 76, ε = 150 µm, Ø_max = 200 mm
  nb_max(200) = π × (200² − 76²) / (4 × 0.15 × 80)
            ≈ π × (40000 − 5776) / 48
            ≈ π × 712.99…  ≈ 2240   (cf helper CC2 exact)
  Donc « ~3000 » dans le brief est une approximation ; on s'en tient
  aux valeurs exactes du helper SSOT.

Cost rebobinage : LECTURE SEULE — on ne teste pas la logique d'
`arbitrage_mandrins`, juste qu'on l'appelle avec le bon `nb_bobines`
et qu'on récupère un Decimal cohérent.
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.planificateur_bobines import calculer_plan_bobines
from app.services.rebobinage.types import (
    MachineRebobinageParams,
    ParametresMandrinRuntime,
    TarifsMandrins,
)


_client = TestClient(app)


# ---------------------------------------------------------------------------
# Cas type brief — Q=10000, n_laize=3, Ø=200
# ---------------------------------------------------------------------------


def _inputs_cas_type():
    return {
        "quantite_commandee": 10_000,
        "n_laize": 3,
        "pas_mm": 80.0,
        "mandrin_mm": 76,
        "diametre_max_bobine_mm": 200.0,
        "epaisseur_matiere_um": 150.0,
    }


def test_cas_type_R_et_nb_max():
    """Vérifie les invariants de base (R, nb_max) sur le cas brief."""
    res = calculer_plan_bobines(**_inputs_cas_type())
    # R = ceil(10000/3) = 3334 → R*n_laize = 10002, surprod = 2.
    sc_A = next(s for s in res.scenarios if s.cle == "A")
    assert sc_A.quantite_totale_etiq == 3334 * 3  # 10002
    assert sc_A.surprod_etiq == 2
    # nb_max = π × (200² − 76²) / (4 × 0.15 × 80) ≈ 2240 (helper exact).
    # nb_max = π × (200² − 76²) / (4 × 0.15 × 80) ≈ 2239.83 → floor = 2239.
    assert res.nb_max_par_bobine == 2239


def test_scenario_A_pleines_plus_reliquat():
    """k bobines de nb_max + 1 partielle si reste > 0."""
    res = calculer_plan_bobines(**_inputs_cas_type())
    sc_A = next(s for s in res.scenarios if s.cle == "A")
    # R = 3334, nb_max = 2239 → k = 1, reste = 1095.
    # Par piste : 1 × 2239 + 1 × 1095 = 2 bobines/piste.
    # Total = 2 × 3 = 6 bobines.
    assert sc_A.nb_bobines_par_piste == 2
    assert sc_A.nb_bobines_total == 6
    tailles = [r.nb_etiq_par_bobine for r in sc_A.repartition]
    assert tailles == [2239, 1095]


def test_scenario_B_equilibrees():
    """k = ceil(R/nb_max) bobines ~égales."""
    res = calculer_plan_bobines(**_inputs_cas_type())
    sc_B = next(s for s in res.scenarios if s.cle == "B")
    # R = 3334, nb_max = 2240 → k = 2 → taille = ceil(3334/2) = 1667.
    # (k-1) à 1667 + dernière 1667 → toutes égales à 1667.
    assert sc_B.nb_bobines_par_piste == 2
    assert sc_B.nb_bobines_total == 6
    # Toutes les bobines doivent tenir ≤ nb_max.
    for r in sc_B.repartition:
        assert r.nb_etiq_par_bobine <= res.nb_max_par_bobine


def test_scenario_C_tomber_juste_inf_et_sup():
    """C_inf : Q' ≤ Q sans reliquat. C_sup : Q' ≥ Q sans reliquat."""
    res = calculer_plan_bobines(**_inputs_cas_type())
    sc_inf = next((s for s in res.scenarios if s.cle == "C_inf"), None)
    sc_sup = next((s for s in res.scenarios if s.cle == "C_sup"), None)
    assert sc_inf is not None and sc_sup is not None
    # Tailles pleines (1 seule taille en répartition).
    assert len(sc_inf.repartition) == 1
    assert len(sc_sup.repartition) == 1
    # Pas de reliquat = R' divisible par k.
    R_inf = sc_inf.quantite_totale_etiq // 3
    R_sup = sc_sup.quantite_totale_etiq // 3
    assert R_inf % sc_inf.nb_bobines_par_piste == 0
    assert R_sup % sc_sup.nb_bobines_par_piste == 0
    # q_ajustee remontée vs Q saisi.
    assert sc_inf.q_ajustee == sc_inf.quantite_totale_etiq
    assert sc_sup.q_ajustee == sc_sup.quantite_totale_etiq
    assert sc_inf.q_ajustee <= 10_000 <= sc_sup.q_ajustee


# ---------------------------------------------------------------------------
# Surprod / Ø helper / cas indivisible
# ---------------------------------------------------------------------------


def test_surprod_coherent_avec_R_x_n_laize():
    """surprod = R × n_laize − Q dans tous les scénarios A/B (production réelle)."""
    res = calculer_plan_bobines(**_inputs_cas_type())
    R_x_n = 3334 * 3
    for sc in res.scenarios:
        if sc.cle in ("A", "B"):
            assert sc.surprod_etiq == R_x_n - 10_000


def test_diametres_consistents_avec_helper_ssot_cc2():
    """Ø affichés viennent strictement de `calcul_diametre_requis_pour_nb_etiq`.

    On rejoue le helper indépendamment et on compare aux valeurs du scénario.
    """
    from app.services.optimisation.bat_calculs import (
        calcul_diametre_requis_pour_nb_etiq,
    )

    inputs = _inputs_cas_type()
    res = calculer_plan_bobines(**inputs)
    sc_A = next(s for s in res.scenarios if s.cle == "A")
    for r in sc_A.repartition:
        d_helper = calcul_diametre_requis_pour_nb_etiq(
            nb_etiq=r.nb_etiq_par_bobine,
            mandrin_mm=inputs["mandrin_mm"],
            epaisseur_matiere_um=inputs["epaisseur_matiere_um"],
            pas_mm=inputs["pas_mm"],
        )
        assert r.diametre_mm == d_helper


def test_Q_indivisible_traite_arrondi_haut():
    """Q = 7 sur n_laize = 3 → R = 3, R × n_laize = 9, surprod = 2."""
    res = calculer_plan_bobines(
        quantite_commandee=7,
        n_laize=3,
        pas_mm=80.0,
        mandrin_mm=76,
        diametre_max_bobine_mm=200.0,
        epaisseur_matiere_um=150.0,
    )
    sc_A = next(s for s in res.scenarios if s.cle == "A")
    assert sc_A.quantite_totale_etiq == 9
    assert sc_A.surprod_etiq == 2


# ---------------------------------------------------------------------------
# Coût via cost_engine LECTURE SEULE
# ---------------------------------------------------------------------------


def _machine_default():
    return MachineRebobinageParams(
        vitesse_pratique_m_min=100,
        cout_horaire_eur=Decimal("45.00"),
        temps_changement_bobine_min=Decimal("0.5"),
    )


def _tarifs_default():
    return TarifsMandrins(
        prix_pre_coupe_par_mandrin_eur=Decimal("5.00"),
        cout_decoupe_interne_par_mandrin_eur=Decimal("2.00"),
        cout_fixe_decoupe_interne_eur=Decimal("39.00"),
    )


def test_cout_rebobinage_calcule_si_machine_tarifs_fournis():
    """Le cost est non-None, recommande_cle non-None, mode_optimal renseigné."""
    res = calculer_plan_bobines(
        **_inputs_cas_type(),
        machine=_machine_default(),
        tarifs=_tarifs_default(),
        parametres=ParametresMandrinRuntime(scie_disponible=True),
    )
    # Tous les scénarios A/B/C ont un coût.
    for sc in res.scenarios:
        if sc.cle in ("A", "B", "C_inf", "C_sup"):
            assert sc.cout_total_eur is not None
            assert sc.cout_machine_eur is not None
            assert sc.cout_mandrins_eur is not None
            assert sc.mode_mandrins_optimal in ("pre_coupe", "decoupe_interne")
    # Recommandation pointe vers le moins cher (A/B/C uniquement).
    assert res.recommande_cle in ("A", "B", "C_inf", "C_sup")


def test_cout_None_si_machine_ou_tarifs_absents():
    """Sans machine NI tarifs → tous les cost = None, pas de recommandation."""
    res = calculer_plan_bobines(**_inputs_cas_type())
    for sc in res.scenarios:
        assert sc.cout_total_eur is None
    assert res.recommande_cle is None


# ---------------------------------------------------------------------------
# Scénario IMPOSE — anti-fléau
# ---------------------------------------------------------------------------


def test_impose_dans_la_plage_carte_visible_sans_alerte_impossible():
    """nb_impose ≤ nb_max → carte IMPOSE OK, alerte non-impossible."""
    res = calculer_plan_bobines(
        **_inputs_cas_type(),
        nb_etiq_impose=1_500,  # < nb_max ≈ 2240
    )
    sc_impose = next((s for s in res.scenarios if s.cle == "IMPOSE"), None)
    assert sc_impose is not None
    assert sc_impose.repartition[0].nb_etiq_par_bobine == 1_500
    assert res.alerte_impose is not None
    assert res.alerte_impose.nb_impose == 1_500
    assert res.alerte_impose.nb_realisable_max == 2239
    assert res.alerte_impose.physiquement_impossible is False


def test_impose_au_dessus_de_nb_max_signale_physiquement_impossible():
    """nb_impose > nb_max → flag physiquement_impossible, Ø requis remonté."""
    res = calculer_plan_bobines(
        **_inputs_cas_type(),
        nb_etiq_impose=3_000,  # > nb_max ≈ 2240
    )
    assert res.alerte_impose is not None
    assert res.alerte_impose.physiquement_impossible is True
    # Ø qu'exigerait 3000 étiq > Ø max client (200).
    assert res.alerte_impose.diametre_requis_mm > 200


def test_impose_pas_dans_recommande():
    """La recommandation ignore IMPOSE même si son coût est le plus bas."""
    res = calculer_plan_bobines(
        **_inputs_cas_type(),
        nb_etiq_impose=1_000,
        machine=_machine_default(),
        tarifs=_tarifs_default(),
        parametres=ParametresMandrinRuntime(scie_disponible=True),
    )
    assert res.recommande_cle != "IMPOSE"


# ---------------------------------------------------------------------------
# Endpoint smoke
# ---------------------------------------------------------------------------


def test_endpoint_smoke_cas_type():
    payload = _inputs_cas_type()
    r = _client.post("/api/devis/planificateur-bobines", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "scenarios" in data
    cles = [s["cle"] for s in data["scenarios"]]
    assert "A" in cles and "B" in cles
    assert data["nb_max_par_bobine"] == 2239


def test_endpoint_avec_impose_renvoie_alerte():
    payload = _inputs_cas_type() | {"nb_etiq_impose": 3_000}
    r = _client.post("/api/devis/planificateur-bobines", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["alerte_impose"]["physiquement_impossible"] is True


def test_endpoint_422_si_dmax_inferieur_mandrin():
    payload = _inputs_cas_type() | {"diametre_max_bobine_mm": 50.0}
    r = _client.post("/api/devis/planificateur-bobines", json=payload)
    assert r.status_code == 422
