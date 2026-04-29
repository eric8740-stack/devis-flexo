"""Smoke tests end-to-end Sprint 4 (Lot 4g) — pipeline complet.

Vérifie que le pipeline calcul → persistance → relecture → duplication →
suppression fonctionne avec les VRAIES réponses du moteur cost_engine
(pas des payloads simulés). Inclut la non-régression V1a SACRÉ
(HT 1449.09 € préservé) + V1a matching.

Tests indépendants des libs PDF (le test PDF e2e est dans test_pdf_service).
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_devis_table():
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()


def _v1a_input_manuel() -> dict:
    """Cas médian V1a manuel — HT figé 1449.09 € depuis Sprint 3."""
    return {
        "complexe_id": 31,
        "laize_utile_mm": 220,
        "ml_total": 3000,
        "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
        "machine_id": 1,
        "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
    }


def _v1a_input_matching() -> dict:
    return _v1a_input_manuel() | {"mode_calcul": "matching"}


# ---------------------------------------------------------------------------
# E2E V1a manuel : calcul → save → read → HT 1449.09 préservé
# ---------------------------------------------------------------------------


def test_e2e_v1a_manuel_calcul_then_save_preserves_ht_sacre():
    """V1a manuel : POST /api/cost/calculer → POST /api/devis → GET → HT 1449.09 EXACT."""
    # 1. Calcul via le vrai moteur (non-régression sacrée)
    r_calc = client.post("/api/cost/calculer", json=_v1a_input_manuel())
    assert r_calc.status_code == 200
    output = r_calc.json()
    assert Decimal(output["prix_vente_ht_eur"]) == Decimal("1449.09")
    assert Decimal(output["prix_au_mille_eur"]) == Decimal("6.92")

    # 2. Sauvegarde
    payload_save = {
        "payload_input": _v1a_input_manuel()
        | {
            "format_etiquette_largeur_mm": 60,
            "format_etiquette_hauteur_mm": 40,
            "nb_poses_largeur": 3,
            "nb_poses_developpement": 1,
        },
        "payload_output": output,
    }
    r_save = client.post("/api/devis", json=payload_save)
    assert r_save.status_code == 201
    saved = r_save.json()
    assert Decimal(saved["ht_total_eur"]) == Decimal("1449.09")
    assert saved["mode_calcul"] == "manuel"

    # 3. Relecture vérifie persistance
    r_get = client.get(f"/api/devis/{saved['id']}")
    assert r_get.status_code == 200
    detail = r_get.json()
    assert (
        Decimal(detail["payload_output"]["prix_vente_ht_eur"])
        == Decimal("1449.09")
    )


# ---------------------------------------------------------------------------
# E2E V1a matching : 3 candidats sauvegardés avec cylindre choisi
# ---------------------------------------------------------------------------


def test_e2e_v1a_matching_persists_cylindre_choisi():
    """V1a matching : 3 candidats Z=134/121/108, sauvegarde avec Z=134."""
    r_calc = client.post("/api/cost/calculer", json=_v1a_input_matching())
    assert r_calc.status_code == 200
    output = r_calc.json()
    assert output["mode"] == "matching"
    assert len(output["candidats"]) == 3
    z_list = [c["z"] for c in output["candidats"]]
    assert z_list == [134, 121, 108]

    # Sauvegarde avec Z=134 (premier candidat = meilleur prix au mille)
    chosen = output["candidats"][0]
    payload_save = {
        "payload_input": _v1a_input_matching()
        | {
            "format_etiquette_largeur_mm": 60,
            "format_etiquette_hauteur_mm": 40,
            "nb_poses_largeur": 3,
            "nb_poses_developpement": 1,
        },
        "payload_output": output,
        "cylindre_choisi_z": chosen["z"],
        "cylindre_choisi_nb_etiq": chosen["nb_etiq_par_tour"],
    }
    r_save = client.post("/api/devis", json=payload_save)
    assert r_save.status_code == 201
    saved = r_save.json()
    assert saved["mode_calcul"] == "matching"
    assert saved["cylindre_choisi_z"] == 134
    assert saved["cylindre_choisi_nb_etiq"] == 10
    # HT identique entre candidats (Sprint 7 V2 invariant)
    assert Decimal(saved["ht_total_eur"]) == Decimal("1449.09")


# ---------------------------------------------------------------------------
# E2E pipeline complet : create → list → duplicate → delete → 404
# ---------------------------------------------------------------------------


def test_e2e_pipeline_create_list_duplicate_delete():
    # Création
    r_calc = client.post("/api/cost/calculer", json=_v1a_input_manuel())
    payload_save = {
        "payload_input": _v1a_input_manuel()
        | {
            "format_etiquette_largeur_mm": 60,
            "format_etiquette_hauteur_mm": 40,
            "nb_poses_largeur": 3,
            "nb_poses_developpement": 1,
        },
        "payload_output": r_calc.json(),
    }
    r1 = client.post("/api/devis", json=payload_save)
    devis1_id = r1.json()["id"]
    devis1_numero = r1.json()["numero"]

    # Liste : 1 entrée
    r_list = client.get("/api/devis")
    assert r_list.status_code == 200
    assert r_list.json()["total"] == 1

    # Duplication : nouveau numéro, statut brouillon, mêmes payloads
    r_dup = client.post(f"/api/devis/{devis1_id}/duplicate")
    assert r_dup.status_code == 201
    dup = r_dup.json()
    assert dup["id"] != devis1_id
    assert dup["numero"] != devis1_numero
    assert dup["statut"] == "brouillon"
    assert Decimal(dup["ht_total_eur"]) == Decimal("1449.09")

    # Liste : 2 entrées maintenant
    assert client.get("/api/devis").json()["total"] == 2

    # Suppression du source
    r_del = client.delete(f"/api/devis/{devis1_id}")
    assert r_del.status_code == 204

    # GET source → 404
    assert client.get(f"/api/devis/{devis1_id}").status_code == 404

    # Le duplicata existe toujours
    assert client.get(f"/api/devis/{dup['id']}").status_code == 200


# ---------------------------------------------------------------------------
# Non-régression : moteur cost_engine intact malgré l'ajout Sprint 4
# ---------------------------------------------------------------------------


def test_e2e_non_regression_v1a_manuel_sacre():
    """Garde-fou critique Sprint 4 : V1a manuel reste à 1449.09 € EXACT
    après tout l'ajout de la persistance + PDF + frontend."""
    r = client.post("/api/cost/calculer", json=_v1a_input_manuel())
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "manuel"
    assert Decimal(data["cout_revient_eur"]) == Decimal("1228.04")
    assert Decimal(data["pct_marge_appliquee"]) == Decimal("0.18")
    assert Decimal(data["prix_vente_ht_eur"]) == Decimal("1449.09")
    assert Decimal(data["prix_au_mille_eur"]) == Decimal("6.92")


def test_e2e_non_regression_v1a_matching_3_candidats():
    """Garde-fou critique Sprint 4 : V1a matching = 3 candidats Z=134/121/108
    avec HT identique 1449.09 € + prix_au_mille 7.00 €."""
    r = client.post("/api/cost/calculer", json=_v1a_input_matching())
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "matching"
    assert len(data["candidats"]) == 3
    couples = [(c["z"], c["nb_etiq_par_tour"]) for c in data["candidats"]]
    assert couples == [(134, 10), (121, 9), (108, 8)]
    for c in data["candidats"]:
        assert Decimal(c["prix_vente_ht_eur"]) == Decimal("1449.09")
        assert Decimal(c["prix_au_mille_eur"]) == Decimal("7.00")
