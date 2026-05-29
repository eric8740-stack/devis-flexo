"""Tests — extension planificateur : imposer nb_bobines + packaging + surplus.

Brief CC2 :
- packaging 40×1000 sur 3 pistes → 42 produites + 2 surplus + 2000 étiq surplus
- les 3 décisions ajustent la Q correctement (facture / stock / réduire)
- nb_bobines multiple de n_laize → 0 surplus
- cas impossible (étiq/bobine > nb_max) → physiquement_impossible
- mutex modes IMPOSE (nb_etiq vs nb_bobines vs packaging)
"""
from fastapi.testclient import TestClient

from app.main import app
from app.services.planificateur_bobines import calculer_plan_bobines


_client = TestClient(app)


def _inputs_base():
    """Geometrie nominale : Q=10000, n_laize=3, mandrin 76, ε 150, Dmax 200."""
    return {
        "quantite_commandee": 10_000,
        "n_laize": 3,
        "pas_mm": 80.0,
        "mandrin_mm": 76,
        "diametre_max_bobine_mm": 200.0,
        "epaisseur_matiere_um": 150.0,
    }


# ---------------------------------------------------------------------------
# Mode IMPOSE nb_bobines — étiq/bobine dérivé + surplus
# ---------------------------------------------------------------------------


def test_impose_nb_bobines_demande_multiple_de_n_laize_zero_surplus():
    """40 bobines × 3 pistes : 42 demandé mais 42 = 14 sets × 3 → ratio exact.

    Si nb_bobines_demande est multiple de n_laize, nb_sets × n_laize est
    exactement nb_bobines_demande → surplus = 0.
    """
    res = calculer_plan_bobines(**_inputs_base(), nb_bobines_impose=42)
    sc = next((s for s in res.scenarios if s.cle == "IMPOSE"), None)
    assert sc is not None
    assert sc.nb_bobines_demande == 42
    assert sc.nb_bobines_total == 42  # production = demandé
    assert sc.surplus_bobines == 0
    assert sc.surplus_etiq == 0


def test_impose_nb_bobines_demande_non_multiple_surplus_calcule():
    """40 bobines, 3 pistes → ceil(40/3)=14 sets × 3 = 42 produites, 2 surplus."""
    res = calculer_plan_bobines(**_inputs_base(), nb_bobines_impose=40)
    sc = next((s for s in res.scenarios if s.cle == "IMPOSE"), None)
    assert sc is not None
    assert sc.nb_bobines_demande == 40
    assert sc.nb_bobines_par_piste == 14  # nb_sets
    assert sc.nb_bobines_total == 42  # production réelle
    assert sc.surplus_bobines == 2


def test_impose_nb_bobines_etiq_par_bobine_derive():
    """Étiq/bobine doit être ceil(R / nb_sets), pas une valeur arbitraire."""
    # R = ceil(10000 / 3) = 3334. nb_sets = 14 → étiq/bobine = ceil(3334/14) = 239.
    res = calculer_plan_bobines(**_inputs_base(), nb_bobines_impose=40)
    sc = next(s for s in res.scenarios if s.cle == "IMPOSE")
    assert sc.repartition[0].nb_etiq_par_bobine == 239


# ---------------------------------------------------------------------------
# Mode IMPOSE packaging — N bobines × X étiq, surplus
# ---------------------------------------------------------------------------


def test_impose_packaging_40_x_1000_sur_3_pistes_42_produites_2_surplus():
    """Cas type brief : 40 bobines × 1000 étiq, 3 pistes → 42 produites, +2."""
    res = calculer_plan_bobines(
        **_inputs_base(),
        nb_bobines_impose=40,
        packaging_nb_etiq_par_bobine=1000,
    )
    sc = next((s for s in res.scenarios if s.cle == "IMPOSE"), None)
    assert sc is not None
    assert sc.nb_bobines_demande == 40
    assert sc.nb_bobines_total == 42  # 14 sets × 3
    assert sc.surplus_bobines == 2
    assert sc.surplus_etiq == 2_000  # 2 bobines × 1000 étiq
    # Étiq/bobine = imposé directement par packaging.
    assert sc.repartition[0].nb_etiq_par_bobine == 1_000


def test_impose_packaging_3_decisions_ajustent_la_q():
    """Les 3 options Q exposées doivent correspondre exactement au brief.

    - facture : 42 × 1000 = 42 000 (production totale)
    - stock   : 40 × 1000 = 40 000 (Q demandée)
    - reduire : 39 bobines (13 sets × 3, multiple < demande) → 39 000
    """
    res = calculer_plan_bobines(
        **_inputs_base(),
        nb_bobines_impose=40,
        packaging_nb_etiq_par_bobine=1000,
    )
    sc = next(s for s in res.scenarios if s.cle == "IMPOSE")
    assert sc.q_si_facture == 42_000
    assert sc.q_si_stock == 40_000
    assert sc.q_si_reduire == 39_000  # floor(40/3)=13 sets × 3 × 1000


def test_impose_packaging_multiple_n_laize_surplus_zero():
    """42 bobines × 1000 sur 3 pistes : 42 = 14×3 multiple exact, 0 surplus."""
    res = calculer_plan_bobines(
        **_inputs_base(),
        nb_bobines_impose=42,
        packaging_nb_etiq_par_bobine=1000,
    )
    sc = next(s for s in res.scenarios if s.cle == "IMPOSE")
    assert sc.surplus_bobines == 0
    assert sc.q_si_facture == sc.q_si_stock == 42_000
    # Reduire reste cohérent même si == stock dans ce cas.
    assert sc.q_si_reduire == 42_000


# ---------------------------------------------------------------------------
# Anti-fléau : étiq/bobine > nb_max(Dmax)
# ---------------------------------------------------------------------------


def test_impose_nb_bobines_etiq_derive_au_dessus_nb_max_alerte_impossible():
    """1 seule bobine demandée → étiq/bobine = R = 3334 > nb_max(200) = 2239.

    Le scénario IMPOSE est exposé pour transparence (« si tu forces, voilà »),
    mais `alerte_impose.physiquement_impossible = True`.
    """
    res = calculer_plan_bobines(**_inputs_base(), nb_bobines_impose=1)
    assert res.alerte_impose is not None
    assert res.alerte_impose.physiquement_impossible is True
    # nb_impose remonté = étiq/bobine effectif, pas la demande client.
    assert res.alerte_impose.nb_impose == 3334


def test_impose_packaging_etiq_par_bobine_au_dessus_nb_max_alerte_impossible():
    """Packaging avec étiq/bobine forcé > nb_max → impossible (forçage requis)."""
    res = calculer_plan_bobines(
        **_inputs_base(),
        nb_bobines_impose=10,
        packaging_nb_etiq_par_bobine=3000,  # > 2239
    )
    assert res.alerte_impose is not None
    assert res.alerte_impose.physiquement_impossible is True


# ---------------------------------------------------------------------------
# Mutex : 3 modes IMPOSE exclusifs
# ---------------------------------------------------------------------------


def test_mutex_nb_etiq_et_nb_bobines_simultanes_value_error():
    inputs = _inputs_base()
    try:
        calculer_plan_bobines(
            **inputs,
            nb_etiq_impose=1500,
            nb_bobines_impose=40,
        )
    except ValueError as e:
        assert "mutuellement exclusifs" in str(e).lower()
    else:
        raise AssertionError("Devait lever ValueError")


def test_mutex_packaging_incomplet_value_error():
    """packaging_nb_etiq_par_bobine sans nb_bobines_impose → erreur."""
    try:
        calculer_plan_bobines(
            **_inputs_base(),
            packaging_nb_etiq_par_bobine=1000,
        )
    except ValueError as e:
        assert "packaging incomplet" in str(e).lower()
    else:
        raise AssertionError("Devait lever ValueError")


# ---------------------------------------------------------------------------
# Endpoint HTTP — smoke + mutex 422
# ---------------------------------------------------------------------------


def test_endpoint_nb_bobines_impose_renvoie_scenario_avec_surplus():
    payload = _inputs_base() | {"nb_bobines_impose": 40}
    r = _client.post("/api/devis/planificateur-bobines", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    sc = next((s for s in data["scenarios"] if s["cle"] == "IMPOSE"), None)
    assert sc is not None
    assert sc["nb_bobines_demande"] == 40
    assert sc["surplus_bobines"] == 2


def test_endpoint_packaging_3_options_q_exposees():
    payload = _inputs_base() | {
        "nb_bobines_impose": 40,
        "packaging_nb_etiq_par_bobine": 1000,
    }
    r = _client.post("/api/devis/planificateur-bobines", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    sc = next(s for s in data["scenarios"] if s["cle"] == "IMPOSE")
    assert sc["q_si_facture"] == 42_000
    assert sc["q_si_stock"] == 40_000
    assert sc["q_si_reduire"] == 39_000


def test_endpoint_mutex_422_si_nb_etiq_plus_nb_bobines():
    payload = _inputs_base() | {
        "nb_etiq_impose": 1500,
        "nb_bobines_impose": 40,
    }
    r = _client.post("/api/devis/planificateur-bobines", json=payload)
    assert r.status_code == 422
    assert "mutuellement exclusifs" in r.text.lower()


def test_endpoint_mutex_422_si_packaging_incomplet():
    payload = _inputs_base() | {"packaging_nb_etiq_par_bobine": 1000}
    r = _client.post("/api/devis/planificateur-bobines", json=payload)
    assert r.status_code == 422
    assert "packaging incomplet" in r.text.lower()


# ---------------------------------------------------------------------------
# Persistance — PlanBobinesSelection enrichie
# ---------------------------------------------------------------------------


def _creer_devis_mini() -> int:
    """Importe le helper du test plan_bobines_selection pour réutiliser le setup."""
    from tests.test_plan_bobines_selection import _creer_devis_mini_avec_payload_input

    return _creer_devis_mini_avec_payload_input()


def test_put_plan_bobines_persiste_impose_type_et_decision():
    devis_id = _creer_devis_mini()
    r = _client.put(
        f"/api/devis/{devis_id}/plan-bobines",
        json={
            "scenario": "IMPOSE",
            "nb_bobine": 1000,
            "nb_bobines_total": 42,
            "politique_reliquat": "pleines_plus_reliquat",
            "impose_type": "packaging",
            "nb_bobines_demande": 40,
            "surplus_bobines": 2,
            "decision_surplus": "facture",
        },
    )
    assert r.status_code == 200, r.text

    devis = _client.get(f"/api/devis/{devis_id}").json()
    pb = devis["payload_input"]["plan_bobines"]
    assert pb["impose_type"] == "packaging"
    assert pb["nb_bobines_demande"] == 40
    assert pb["surplus_bobines"] == 2
    assert pb["decision_surplus"] == "facture"


def test_put_plan_bobines_decision_stock_et_reduire_acceptees():
    devis_id = _creer_devis_mini()
    for decision in ("stock", "reduire"):
        r = _client.put(
            f"/api/devis/{devis_id}/plan-bobines",
            json={
                "scenario": "IMPOSE",
                "nb_bobine": 1000,
                "nb_bobines_total": 42,
                "politique_reliquat": "pleines_plus_reliquat",
                "impose_type": "packaging",
                "nb_bobines_demande": 40,
                "surplus_bobines": 2,
                "decision_surplus": decision,
            },
        )
        assert r.status_code == 200, (decision, r.text)
        pb = _client.get(f"/api/devis/{devis_id}").json()["payload_input"][
            "plan_bobines"
        ]
        assert pb["decision_surplus"] == decision
