"""Tests onglet Stratégique (Brief stratégique v2, Phase 1).

Couvre l'API /api/strategique : singletons couts/changements (get-or-create
+ upsert partiel), collection roulage (CRUD), validation, et isolation
multi-tenant (entreprise_id). Le seed autouse fournit la config template du
tenant démo (entreprise_id=1) avant chaque test.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# config_couts (singleton)
# ---------------------------------------------------------------------------
def test_get_couts_returns_seeded_template_defaults():
    r = client.get("/api/strategique/couts")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["cout_operateur_eur_h"] == 25.0
    assert d["cout_exploitation_machine_eur_h"] == 50.0
    assert d["marge_standard_pct"] == 35.0


def test_put_couts_partial_update_preserve_autres_champs():
    r = client.put("/api/strategique/couts", json={"marge_standard_pct": 42})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["marge_standard_pct"] == 42.0
    # Upsert partiel : les autres champs gardent la valeur template.
    assert d["cout_operateur_eur_h"] == 25.0


def test_put_couts_hors_bornes_422():
    r = client.put("/api/strategique/couts", json={"marge_standard_pct": 150})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# config_changements (singleton)
# ---------------------------------------------------------------------------
def test_get_changements_seeded():
    r = client.get("/api/strategique/changements")
    assert r.status_code == 200, r.text
    assert r.json()["changement_couleur_duree_min"] == 15


def test_put_changements_partial():
    r = client.put(
        "/api/strategique/changements", json={"nettoyage_cout_eur": 40}
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nettoyage_cout_eur"] == 40.0
    assert d["changement_couleur_duree_min"] == 15  # préservé


# ---------------------------------------------------------------------------
# config_roulage (collection)
# ---------------------------------------------------------------------------
def test_get_roulage_seeded_deux_formats():
    r = client.get("/api/strategique/roulage")
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 2
    assert {x["format_libelle"] for x in data} == {"A5", "A4"}


def test_post_put_delete_roulage():
    created = client.post(
        "/api/strategique/roulage",
        json={
            "format_libelle": "100x80",
            "debit_mm_s": 300,
            "mode_roulage": "custom",
            "rebut_pct": 4,
        },
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    assert created.json()["mode_roulage"] == "custom"

    upd = client.put(
        f"/api/strategique/roulage/{rid}", json={"debit_mm_s": 320}
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["debit_mm_s"] == 320

    deleted = client.delete(f"/api/strategique/roulage/{rid}")
    assert deleted.status_code == 204


def test_post_roulage_mode_invalide_422():
    r = client.post(
        "/api/strategique/roulage",
        json={
            "format_libelle": "X",
            "debit_mm_s": 200,
            "mode_roulage": "zigzag",  # hors Literal
            "rebut_pct": 2,
        },
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Isolation multi-tenant
# ---------------------------------------------------------------------------
def test_roulage_isolation_user_b(as_user_b):
    """User B (entreprise_id=2) ne voit aucun roulage du tenant démo."""
    r = client.get("/api/strategique/roulage")
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_couts_get_or_create_pour_user_b(as_user_b):
    """User B obtient sa propre config coûts créée à la volée (template)."""
    r = client.get("/api/strategique/couts")
    assert r.status_code == 200, r.text
    assert r.json()["marge_standard_pct"] == 35.0


def test_update_roulage_autre_tenant_404(as_user_b):
    """User B ne peut pas modifier un roulage du tenant 1 (scope 404)."""
    # En tant qu'admin tenant 1, on connaît les ids 1/2 seedés ; user B
    # ciblant l'id 1 doit recevoir 404 (get_or_404_scoped).
    r = client.put("/api/strategique/roulage/1", json={"debit_mm_s": 999})
    assert r.status_code == 404
