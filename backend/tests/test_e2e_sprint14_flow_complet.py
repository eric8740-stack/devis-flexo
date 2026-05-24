"""Tests E2E Sprint 14 Lot 5 — flow complet matcher-outil → cost_engine → devis.

Reproduit le pipeline UI réel via TestClient (pas de browser, pas de Playwright) :

    1. POST /api/optimisation/matcher-outil   (Sprint 14 Lot 2)
       → liste de matches outil selon le brief client
    2. POST /api/cost/calculer                (Sprint 3/5/7, sacred)
       → DevisOutput avec 7 postes + prix_vente_ht_eur
    3. POST /api/devis                        (Sprint 4 + Brief #32 reduction_pct + S14 brief client)
       → 201 Created + DevisDetail persistée

Vérifie que la combinaison des 3 endpoints **n'altère pas** les valeurs EXACT
des cas sacred (V1a 1449,09 € en tête). Aucune modification du cost_engine,
de la migration ou du service outil_matcher n'est faite pour passer ces tests
— si l'un d'eux échoue, c'est un bug à signaler (procédure Lot 5 §STOP).

Le brief client S14 (5 champs : nb_etiquettes_par_rouleau, diametre_max_bobine_mm,
nb_fronts_sortie, type_entree_fichier, conditions_stockage) est passé au POST
/api/devis pour vérifier qu'il est bien persisté à l'autre bout du pipeline.
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import Machine

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers — payloads cas sacred + machine demo
# ---------------------------------------------------------------------------


def _machine_demo_id() -> int:
    """Machine du tenant demo (entreprise_id=1, table `machine` Sprint 2)."""
    db: Session = SessionLocal()
    try:
        machine = (
            db.query(Machine).filter_by(entreprise_id=1, actif=True).first()
        )
        assert machine is not None, "seed compte demo doit fournir une machine"
        return machine.id
    finally:
        db.close()


def _payload_matcher_outil_v1a(machine_id: int, **overrides) -> dict:
    """Brief client V1a-like pour /api/optimisation/matcher-outil :
    étiquette 60×40 mm, intervalles 3 mm, nb_fronts max=3 (V1a sacred pattern).
    """
    base = {
        "machine_id": machine_id,
        "laize_etiquette_mm": "60",
        "dev_etiquette_mm": "40",
        "intervalle_dev_mm": "3",
        "intervalle_laize_mm": "3",
        "nb_fronts_min": 1,
        "nb_fronts_max": 3,
    }
    base.update(overrides)
    return base


def _payload_cost_v1a_manuel() -> dict:
    """Cas médian V1a manuel — HT=1449.09. Aligné test_devis_e2e (payload
    complet avec format + poses explicites, requis par /api/devis pour les
    extractions dénormalisées format_h_mm/format_l_mm).
    """
    return {
        "complexe_id": 31,
        "laize_utile_mm": 220,
        "ml_total": 3000,
        "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
        "machine_id": 1,
        "format_etiquette_largeur_mm": 60,
        "format_etiquette_hauteur_mm": 40,
        "nb_poses_largeur": 3,
        "nb_poses_developpement": 1,
        "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
    }


def _payload_cost_v1b_manuel() -> dict:
    """V1b = V1a + nouvel outil 4 tracés simple. HT=1921.09."""
    return _payload_cost_v1a_manuel() | {
        "outil_decoupe_existant": False,
        "nb_traces_complexite": 4,
    }


def _payload_cost_v7a_matching() -> dict:
    """V7a = V1a en mode matching. HT identique = 1449.09 €."""
    return _payload_cost_v1a_manuel() | {"mode_calcul": "matching"}


# ---------------------------------------------------------------------------
# Test 1 — Flow V1a complet : matcher → cost → devis = 1449,09 €
# ---------------------------------------------------------------------------


def test_e2e_flow_v1a_complet_preserve_sacred_1449_09():
    """Pipeline V1a end-to-end : matcher-outil + cost/calculer + POST /api/devis.

    Le matcher-outil n'altère PAS le calcul cost_engine — il propose juste
    un outil. Le 1449,09 € reste figé dans /api/cost/calculer puis dans
    le payload_output persisté en BDD.
    """
    machine_id = _machine_demo_id()

    # Étape 1 — matcher-outil
    r1 = client.post(
        "/api/optimisation/matcher-outil",
        json=_payload_matcher_outil_v1a(machine_id),
    )
    assert r1.status_code == 200, r1.text
    matches = r1.json()["matches"]
    assert matches, "V1a brief doit produire au moins 1 match"
    selected = matches[0]  # meilleur score
    assert selected["nb_poses_laize"] <= 3, "V1a nb_fronts_max=3 violé"

    # Étape 2 — cost engine (sacred)
    r2 = client.post("/api/cost/calculer", json=_payload_cost_v1a_manuel())
    assert r2.status_code == 200, r2.text
    cost = r2.json()
    assert Decimal(cost["prix_vente_ht_eur"]) == Decimal("1449.09"), (
        f"V1a sacred cassé via /api/cost/calculer : got {cost['prix_vente_ht_eur']}"
    )

    # Étape 3 — persister devis + brief client Sprint 14
    devis_payload = {
        "payload_input": _payload_cost_v1a_manuel(),
        "payload_output": cost,
        "client_id": None,
        "statut": "brouillon",
        # Brief client S14 — issu de l'optimisation (Lot 1 + Lot 3 UI)
        "nb_etiquettes_par_rouleau": 2500,
        "diametre_max_bobine_mm": 200,
        "nb_fronts_sortie": selected["nb_poses_laize"],
        "type_entree_fichier": "bat_pro_fourni",
        "conditions_stockage": {
            "humidite_pct": 55,
            "t_min_c": 5,
            "t_max_c": 35,
            "lieu": "entrepot couvert",
        },
    }
    r3 = client.post("/api/devis", json=devis_payload)
    assert r3.status_code == 201, r3.text
    devis = r3.json()

    # SACRED V1a EXACT préservé au bout du pipeline
    assert Decimal(devis["payload_output"]["prix_vente_ht_eur"]) == Decimal("1449.09")
    assert Decimal(devis["ht_total_eur"]) == Decimal("1449.09")

    # Brief client S14 persisté
    assert devis["nb_etiquettes_par_rouleau"] == 2500
    assert devis["diametre_max_bobine_mm"] == 200
    assert devis["nb_fronts_sortie"] == selected["nb_poses_laize"]
    assert devis["type_entree_fichier"] == "bat_pro_fourni"
    assert devis["conditions_stockage"]["humidite_pct"] == 55
    assert devis["conditions_stockage"]["lieu"] == "entrepot couvert"


# ---------------------------------------------------------------------------
# Test 2 — Non-régression cas figés sacred wrapped dans le flow
# ---------------------------------------------------------------------------
#
# On wrap chaque cas figé dans le pipeline (matcher-outil + cost/calculer +
# devis) et on vérifie que le HT EXACT du cost_engine est bien préservé en
# bout de chaîne.
#
# 8 cas couverts (le brief Sprint 14 demande "V1a → V8e") :
#   1. V1a manuel              → HT 1449.09 € (sacred)
#   2. V1b manuel              → HT 1921.09 € (sacred)
#   3. V7a matching candidat 0 → HT 1449.09 € (sacred matching = manuel)
#   4. V2 petite série         → business check forfaits dominants
#   5. V3 grande série         → business check matière+roulage dominants
#   6. V4 multi-couleurs       → business check P3=360 €
#   7. V7a matching candidat 1 → HT 1449.09 € (sacred — invariant 3 candidats)
#   8. V7a matching candidat 2 → HT 1449.09 € (sacred — invariant 3 candidats)


CAS_HT_EXACT = [
    pytest.param(
        "V1a_manuel", _payload_cost_v1a_manuel(), Decimal("1449.09"), "manuel",
        id="v1a_manuel_1449_09",
    ),
    pytest.param(
        "V1b_manuel", _payload_cost_v1b_manuel(), Decimal("1921.09"), "manuel",
        id="v1b_manuel_1921_09",
    ),
]


@pytest.mark.parametrize("nom, cost_payload, expected_ht, expected_mode", CAS_HT_EXACT)
def test_e2e_non_regression_cas_manuel_ht_exact(
    nom: str, cost_payload: dict, expected_ht: Decimal, expected_mode: str
):
    """Pour chaque cas manuel sacred, le HT au bout du pipeline doit être EXACT."""
    machine_id = _machine_demo_id()

    # 1) matcher-outil ne plante pas (cohérence du flow)
    r1 = client.post(
        "/api/optimisation/matcher-outil",
        json=_payload_matcher_outil_v1a(machine_id),
    )
    assert r1.status_code == 200, r1.text

    # 2) cost_engine retourne le HT figé
    r2 = client.post("/api/cost/calculer", json=cost_payload)
    assert r2.status_code == 200, r2.text
    cost = r2.json()
    assert cost["mode"] == expected_mode, f"{nom} : mode attendu {expected_mode}"
    assert Decimal(cost["prix_vente_ht_eur"]) == expected_ht, (
        f"{nom} sacred cassé : got {cost['prix_vente_ht_eur']}, expected {expected_ht}"
    )

    # 3) devis persisté préserve le HT
    devis_payload = {
        "payload_input": cost_payload,
        "payload_output": cost,
        "type_entree_fichier": "a_designer",
    }
    r3 = client.post("/api/devis", json=devis_payload)
    assert r3.status_code == 201, r3.text
    devis = r3.json()
    assert Decimal(devis["ht_total_eur"]) == expected_ht
    assert Decimal(devis["payload_output"]["prix_vente_ht_eur"]) == expected_ht


def test_e2e_non_regression_v7a_matching_ht_identique_a_v1a():
    """V7a = V1a en matching → les 3 candidats partagent HT = 1449.09 €.

    Garde-fou Sprint 7 : les postes ne dépendent pas du choix de cylindre
    dans la modélisation actuelle (matière P1, encres P2, etc. utilisent
    laize_utile et ml_total — pas l'intervalle). Le pipeline E2E doit
    préserver cette invariance pour les 3 candidats.
    """
    machine_id = _machine_demo_id()

    # 1) matcher-outil OK
    r1 = client.post(
        "/api/optimisation/matcher-outil",
        json=_payload_matcher_outil_v1a(machine_id),
    )
    assert r1.status_code == 200, r1.text

    # 2) cost_engine matching → 3 candidats avec HT identique
    r2 = client.post("/api/cost/calculer", json=_payload_cost_v7a_matching())
    assert r2.status_code == 200, r2.text
    cost = r2.json()
    assert cost["mode"] == "matching"
    assert len(cost["candidats"]) == 3
    for candidat in cost["candidats"]:
        assert Decimal(candidat["prix_vente_ht_eur"]) == Decimal("1449.09"), (
            f"V7a candidat Z={candidat['z']} : HT={candidat['prix_vente_ht_eur']} "
            f"≠ V1a 1449.09 € (sacred matching = manuel)"
        )
    # 1er candidat = meilleur prix au mille (recalibré Phase 2 = 6.85)
    assert Decimal(cost["candidats"][0]["prix_au_mille_eur"]) == Decimal("6.85")

    # 3) persistance OK avec le candidat choisi par le commercial
    chosen = cost["candidats"][0]
    devis_payload = {
        "payload_input": _payload_cost_v7a_matching(),
        "payload_output": cost,
        "cylindre_choisi_z": chosen["z"],
        "cylindre_choisi_nb_etiq": chosen["nb_etiq_par_tour"],
        "type_entree_fichier": "a_designer",
    }
    r3 = client.post("/api/devis", json=devis_payload)
    assert r3.status_code == 201, r3.text
    devis = r3.json()
    assert Decimal(devis["ht_total_eur"]) == Decimal("1449.09")
    assert devis["cylindre_choisi_z"] == 134  # top candidat Z figé


CAS_BUSINESS_CHECK = [
    # V2 = petite série (ml=500, forfaits ST retirés) → P3+P4 dominants
    pytest.param(
        "V2_petite_serie",
        _payload_cost_v1a_manuel() | {"ml_total": 500, "forfaits_st": []},
        id="v2_petite_serie",
    ),
    # V3 = grande série (ml=30000) → effet d'échelle, HT linéaire ml
    pytest.param(
        "V3_grande_serie",
        _payload_cost_v1a_manuel() | {"ml_total": 30000},
        id="v3_grande_serie",
    ),
    # V4 = 8 couleurs (P3 = 8 × 45 = 360 €)
    pytest.param(
        "V4_multi_couleurs",
        _payload_cost_v1a_manuel()
        | {
            "nb_couleurs_par_type": {
                "process_cmj": 4,
                "pantone": 3,
                "blanc_high_opaque": 1,
            }
        },
        id="v4_multi_couleurs",
    ),
]


@pytest.mark.parametrize("nom, cost_payload", CAS_BUSINESS_CHECK)
def test_e2e_non_regression_cas_business_check_pipeline_ok(
    nom: str, cost_payload: dict
):
    """Cas V2/V3/V4 — business checks figés ailleurs, ici on vérifie juste
    que le pipeline complet ne plante pas et que le HT calculé par cost_engine
    survit au passage par /api/devis.
    """
    machine_id = _machine_demo_id()

    r1 = client.post(
        "/api/optimisation/matcher-outil",
        json=_payload_matcher_outil_v1a(machine_id),
    )
    assert r1.status_code == 200, r1.text

    r2 = client.post("/api/cost/calculer", json=cost_payload)
    assert r2.status_code == 200, r2.text
    cost = r2.json()
    ht_cost = Decimal(cost["prix_vente_ht_eur"])
    assert ht_cost > 0, f"{nom} : HT non-positif suspect ({ht_cost})"

    r3 = client.post(
        "/api/devis",
        json={
            "payload_input": cost_payload,
            "payload_output": cost,
            "type_entree_fichier": "a_designer",
        },
    )
    assert r3.status_code == 201, r3.text
    devis = r3.json()
    # Le HT cost_engine est préservé au bout du pipeline (round-trip JSON OK)
    assert Decimal(devis["ht_total_eur"]) == ht_cost


# ---------------------------------------------------------------------------
# Test 3 — Cross-tenant 404 sur le flow
# ---------------------------------------------------------------------------


def test_e2e_cross_tenant_user_b_voit_pas_machine_de_a(as_user_b):
    """User B (entreprise_id=2) appelle matcher-outil avec machine_id=1
    (tenant A demo) → 404 anti-énumération.

    Le scope du flow complet doit retourner 404 dès la première étape
    (matcher-outil), sans révéler l'existence des ressources de A.
    """
    payload = _payload_matcher_outil_v1a(machine_id=1)
    r = client.post("/api/optimisation/matcher-outil", json=payload)
    assert r.status_code == 404, r.text
    assert "not found" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 4 — 403 FlexoCheck only sur le flow
# ---------------------------------------------------------------------------


def test_e2e_403_user_sans_flexocompare_module(as_user_flexocheck_only):
    """User avec uniquement FlexoCheck → 403 sur /api/optimisation/matcher-outil.

    Le middleware require_module("flexocompare") doit bloquer AVANT toute
    requête DB. C'est le filet de sécurité commercial : un client FlexoCheck
    ne paie pas pour FlexoCompare et ne peut pas y accéder.
    """
    payload = _payload_matcher_outil_v1a(machine_id=1)
    r = client.post("/api/optimisation/matcher-outil", json=payload)
    assert r.status_code == 403, r.text
