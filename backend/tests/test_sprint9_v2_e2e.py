"""Tests E2E Sprint 9 v2 — flux critiques de bout en bout.

Vérifient que les changements via API se propagent bien au moteur et
inversement (reset → restauration des valeurs exact).
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


_PAYLOAD_V1B = {
    "complexe_id": 31,
    "laize_utile_mm": 220,
    "ml_total": 3000,
    "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
    "machine_id": 1,
    "outil_decoupe_existant": False,
    "nb_traces_complexite": 4,
    "forme_speciale": False,
    "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
}


def _calculer(payload: dict) -> Decimal:
    """Helper : POST /api/cost/calculer et retourne prix_vente_ht_eur."""
    r = client.post("/api/cost/calculer", json=payload)
    assert r.status_code == 200, r.text
    return Decimal(str(r.json()["prix_vente_ht_eur"]))


def test_e2e_modif_outil_base_then_reset_returns_v1b_to_1921():
    """Flux critique S9 v2 : modifier tarif → recalculer → reset → V1b EXACT.

    Étapes :
    1. V1b nouvel outil = 1 921,09 € (baseline)
    2. PUT outil_base_eur 200 → 250 (+50)
    3. V1b devient 1 980,09 € (+ 59 = 50 × 1.18 marge)
    4. POST reset poste 3 → 4 paramètres restaurés
    5. V1b retombe à 1 921,09 € EXACT
    """
    # Baseline
    assert _calculer(_PAYLOAD_V1B) == Decimal("1921.09")

    # Modification tarif
    r = client.put(
        "/api/tarif-poste/outil_base_eur", json={"valeur_defaut": "250.00"}
    )
    assert r.status_code == 200
    assert _calculer(_PAYLOAD_V1B) == Decimal("1980.09")

    # Reset poste 3
    r = client.post("/api/tarif-poste/reset/3")
    assert r.status_code == 200
    body = r.json()
    assert body["poste_numero"] == 3
    assert body["n_reset"] == 4  # cliche + 3 outillage

    # V1b retombé à la valeur EXACT seedée
    assert _calculer(_PAYLOAD_V1B) == Decimal("1921.09")


def test_e2e_create_outil_appears_in_default_active_list():
    """Création d'un outil → présent dans GET /api/outils (filtre actif)."""
    r = client.post(
        "/api/outils",
        json={
            "libelle": "outil_e2e_s9_test",
            "format_l_mm": 80,
            "format_h_mm": 50,
            "nb_poses_l": 2,
            "nb_poses_h": 1,
            "forme_speciale": False,
        },
    )
    assert r.status_code == 201
    libelles = {o["libelle"] for o in client.get("/api/outils").json()}
    assert "outil_e2e_s9_test" in libelles
    assert len(libelles) == 5  # 4 seedés + 1 nouveau


def test_e2e_soft_delete_machine_filtered_then_reactiver():
    """Soft delete machine → cachée par défaut → réactivation → re-visible."""
    # Baseline : 3 machines actives (incl. Atelier 2 « maintenance »
    # désormais mappé actif=True après migration S9 v2)
    listed_initial = client.get("/api/machines").json()
    assert len(listed_initial) == 3
    machine_id = listed_initial[0]["id"]  # Mark Andy P5

    # Soft delete
    r = client.delete(f"/api/machines/{machine_id}")
    assert r.status_code == 204

    # Filtre par défaut (actif=True) : 2 machines restantes
    listed_after = client.get("/api/machines").json()
    assert len(listed_after) == 2
    assert machine_id not in [m["id"] for m in listed_after]

    # Avec include_inactives : 3 machines (l'inactive réapparait)
    listed_all = client.get("/api/machines?include_inactives=true").json()
    assert len(listed_all) == 3
    inactive = next(m for m in listed_all if m["id"] == machine_id)
    assert inactive["actif"] is False

    # GET individuel reste accessible
    r = client.get(f"/api/machines/{machine_id}")
    assert r.status_code == 200
    assert r.json()["actif"] is False

    # Réactivation
    r = client.post(f"/api/machines/{machine_id}/reactiver")
    assert r.status_code == 200
    assert r.json()["actif"] is True

    # Liste par défaut reprend les 3 machines
    listed_final = client.get("/api/machines").json()
    assert len(listed_final) == 3
    assert machine_id in [m["id"] for m in listed_final]


def test_e2e_tarif_poste_grouped_contains_10_keys():
    """Snapshot global : 6 postes seedés (1, 3, 4, 5, 6, 7), 10 paramètres."""
    response = client.get("/api/tarif-poste")
    assert response.status_code == 200
    postes = response.json()["postes"]
    assert [p["poste_numero"] for p in postes] == [1, 3, 4, 5, 6, 7]
    assert sum(len(p["parametres"]) for p in postes) == 10
    # Poste 3 a 4 paramètres = cliche_prix_couleur + 3 outillage Sprint 9 v2
    poste_3 = next(p for p in postes if p["poste_numero"] == 3)
    assert {p["cle"] for p in poste_3["parametres"]} == {
        "cliche_prix_couleur",
        "outil_base_eur",
        "outil_par_trace_eur",
        "surcout_forme_speciale_pct",
    }
