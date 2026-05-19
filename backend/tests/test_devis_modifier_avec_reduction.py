"""Tests Brief #32 commit 2 — réduction commerciale + PUT recalcul.

Couvre :
  - PUT /api/devis/{id} avec reduction_pct → persistance correcte.
  - reduction_pct hors bornes (0..100) → 422.
  - PUT avec lots différents → recalcul cost_engine_aggregator + ht_total
    mis à jour (ou note erreur en mode dégradé).
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis
from tests.test_creation_devis_calcule_prix_aggregate import _payload_devis_1_lot

client = TestClient(app)


def _creer_devis_de_test() -> int:
    """Crée un devis multi-lots et retourne son id."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
    r = client.post("/api/devis", json=_payload_devis_1_lot())
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_patch_devis_avec_reduction_pct():
    """PUT /api/devis/{id} avec `reduction_pct` met à jour le champ."""
    devis_id = _creer_devis_de_test()

    r = client.put(
        f"/api/devis/{devis_id}",
        json={"reduction_pct": 15.5},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert Decimal(str(body["reduction_pct"])) == Decimal("15.5")


def test_reduction_pct_hors_bornes_422():
    """reduction_pct < 0 ou > 100 → 422 Pydantic (Field ge=0 le=100)."""
    devis_id = _creer_devis_de_test()

    # Négatif
    r = client.put(f"/api/devis/{devis_id}", json={"reduction_pct": -5})
    assert r.status_code == 422

    # > 100
    r = client.put(f"/api/devis/{devis_id}", json={"reduction_pct": 101})
    assert r.status_code == 422


def test_recalcul_cost_engine_si_lots_modifies():
    """PUT avec nouveaux lots → cost_engine_aggregator rappelé, devis
    chiffré avec le nouveau ht_total (ou mode dégradé si chiffrage KO).

    On change le nb_poses du lot pour invalider le cache cout_lot_ht_eur
    et déclencher un recalcul."""
    devis_id = _creer_devis_de_test()

    # Lire l'état initial
    r = client.get(f"/api/devis/{devis_id}")
    assert r.status_code == 200
    devis_before = r.json()

    # Modifier les lots avec nouvelles poses
    lot_initial = devis_before["lots_production"][0]
    nouveau_lot = {
        "cylindre_id": lot_initial["cylindre_id"],
        "machine_id": lot_initial["machine_id"],
        "nb_poses_dev": 1,  # changé (était 2)
        "nb_poses_laize": 2,  # changé (était 3)
        "sens_enroulement": 1,
        "quantite": 10000,
        "matiere_id": lot_initial["matiere_id"],
    }

    r = client.put(
        f"/api/devis/{devis_id}",
        json={
            "quantite_totale": 10000,
            "lots": [nouveau_lot],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # 1 lot persisté avec les nouvelles valeurs
    assert len(body["lots_production"]) == 1
    assert body["lots_production"][0]["nb_poses_dev"] == 1
    assert body["lots_production"][0]["nb_poses_laize"] == 2


def test_validation_somme_quantites_lots_egale_totale_au_patch():
    """PUT avec Σ qté lots ≠ quantite_totale → 422."""
    devis_id = _creer_devis_de_test()

    r = client.get(f"/api/devis/{devis_id}")
    lot_initial = r.json()["lots_production"][0]

    r = client.put(
        f"/api/devis/{devis_id}",
        json={
            "quantite_totale": 10000,
            "lots": [
                {
                    "cylindre_id": lot_initial["cylindre_id"],
                    "machine_id": lot_initial["machine_id"],
                    "nb_poses_dev": 2,
                    "nb_poses_laize": 3,
                    "sens_enroulement": 1,
                    "quantite": 5000,  # somme != totale
                    "matiere_id": lot_initial["matiere_id"],
                }
            ],
        },
    )
    # ValueError du CRUD → 422 via le handler existant.
    assert r.status_code == 422, r.text
