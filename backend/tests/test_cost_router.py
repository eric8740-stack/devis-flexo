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
