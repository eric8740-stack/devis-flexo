"""Tests intégration HTTP du router /api/cost (S3 Lot 3f).

Vérifie le endpoint POST /api/cost/calculer + la conversion CostEngineError
en HTTP 422 par le handler global de app/main.py.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _payload_median() -> dict:
    """Cas médian aligné sur test_cost_engine_benchmark (HT figé 1449.09 €)."""
    return {
        "complexe_id": 31,
        "laize_utile_mm": 220,
        "ml_total": 3000,
        "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
        "machine_id": 1,
        "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
    }


def test_post_cost_calculer_returns_200_and_full_devis_output():
    response = client.post("/api/cost/calculer", json=_payload_median())
    assert response.status_code == 200
    data = response.json()
    # Sprint 7 : discriminant mode présent (default 'manuel' pour rétrocompat V1a)
    assert data["mode"] == "manuel"
    assert len(data["postes"]) == 7
    assert [p["poste_numero"] for p in data["postes"]] == [1, 2, 3, 4, 5, 6, 7]
    # Cas médian figé Lot 3d
    assert Decimal(data["cout_revient_eur"]) == Decimal("1228.04")
    assert Decimal(data["prix_vente_ht_eur"]) == Decimal("1449.09")
    assert Decimal(data["pct_marge_appliquee"]) == Decimal("0.18")


def test_post_cost_calculer_with_marge_override():
    payload = _payload_median() | {"pct_marge_override": "0.30"}
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["pct_marge_appliquee"]) == Decimal("0.30")
    expected_ht = (Decimal("1228.04") * Decimal("1.30")).quantize(Decimal("0.01"))
    assert Decimal(data["prix_vente_ht_eur"]) == expected_ht


def test_post_cost_calculer_unknown_complexe_returns_422():
    payload = _payload_median() | {"complexe_id": 9999}
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 422
    assert "complexe" in response.json()["detail"].lower()


def test_post_cost_calculer_unknown_type_encre_returns_422():
    payload = _payload_median() | {
        "nb_couleurs_par_type": {"process_xyz_inexistant": 2}
    }
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 422
    assert "type_encre" in response.json()["detail"]


def test_post_cost_calculer_complexe_without_grammage_returns_422():
    """Complexe id=1 (BOPP_BLANC_50) a grammage NULL → CostEngineError → 422."""
    payload = _payload_median() | {"complexe_id": 1}
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 422
    assert "grammage" in response.json()["detail"]


def test_post_cost_calculer_invalid_payload_returns_422_pydantic():
    """Body Pydantic invalide (laize_utile_mm = 0) → 422 par FastAPI/Pydantic."""
    payload = _payload_median() | {"laize_utile_mm": 0}
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 422


def test_post_cost_calculer_extra_field_rejected():
    """extra='forbid' sur DevisInput → champ inconnu rejeté en 422."""
    payload = _payload_median() | {"champ_inconnu": 42}
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Sprint 7 Lot 7e — mode matching (Union response discriminée par 'mode')
# ---------------------------------------------------------------------------


def test_post_cost_calculer_mode_matching_v1a_returns_candidats():
    """V1a en mode matching → DevisOutputMatching avec 1-3 candidats."""
    payload = _payload_median() | {"mode_calcul": "matching"}
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "matching"
    assert "candidats" in data
    assert 1 <= len(data["candidats"]) <= 3
    # Premier candidat = meilleur intervalle (= meilleur prix au mille en premier)
    intervalles = [Decimal(c["intervalle_mm"]) for c in data["candidats"]]
    assert intervalles == sorted(intervalles)
    # Chaque candidat a sa structure complète
    for c in data["candidats"]:
        assert 51 <= c["z"] <= 144
        assert 1 <= c["nb_etiq_par_tour"] <= 40
        assert Decimal("2.5") <= Decimal(c["intervalle_mm"]) <= Decimal("15")
        assert len(c["postes"]) == 7
        # HT identique entre candidats (postes ne dépendent pas du cylindre)
        assert Decimal(c["prix_vente_ht_eur"]) == Decimal("1449.09")


def test_post_cost_calculer_mode_matching_largeur_excede_laize_returns_422():
    """Plaque trop large pour la machine → 422 explicite (handler global)."""
    # Machine 1 (Mark Andy) laize 330, marge 2×5=10, max admissible = 320.
    # Largeur plaque = format_l × nb_poses_largeur = 60 × 6 = 360 mm > 320.
    payload = _payload_median() | {
        "mode_calcul": "matching",
        "nb_poses_largeur": 6,  # 60 × 6 = 360 mm > 320 max
    }
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 422
    assert "laize" in response.json()["detail"].lower()


def test_post_cost_calculer_mode_matching_intervalle_set_rejected():
    """Validateur cross-field DevisInput : intervalle_mm interdit en matching → 422."""
    payload = _payload_median() | {
        "mode_calcul": "matching",
        "intervalle_mm": "3",
    }
    response = client.post("/api/cost/calculer", json=payload)
    assert response.status_code == 422
