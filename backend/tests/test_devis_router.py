"""Tests intégration HTTP /api/devis (Sprint 4 Lot 4b)."""
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixture : table devis vidée avant ET après chaque test pour isoler la
# numérotation séquentielle (count + 1 par année)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_devis_table():
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()


# ---------------------------------------------------------------------------
# Payloads de test
# ---------------------------------------------------------------------------


def _payload_v1a_manuel() -> dict:
    """payload_input + payload_output simulant V1a manuel calculé."""
    return {
        "payload_input": {
            "complexe_id": 31,
            "laize_utile_mm": 220,
            "ml_total": 3000,
            "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
            "machine_id": 1,
            "format_etiquette_largeur_mm": 60,
            "format_etiquette_hauteur_mm": 40,
            "nb_poses_largeur": 3,
            "nb_poses_developpement": 1,
            "mode_calcul": "manuel",
            "intervalle_mm": "3",
            "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
        },
        "payload_output": {
            "mode": "manuel",
            "cout_revient_eur": "1228.04",
            "pct_marge_appliquee": "0.18",
            "prix_vente_ht_eur": "1449.09",
            "prix_au_mille_eur": "6.92",
            "postes": [
                {
                    "poste_numero": i,
                    "libelle": f"P{i}",
                    "montant_eur": "100.00",
                    "details": {},
                }
                for i in range(1, 8)
            ],
        },
    }


def _payload_v1a_matching() -> dict:
    pi = _payload_v1a_manuel()["payload_input"] | {"mode_calcul": "matching"}
    pi.pop("intervalle_mm", None)
    return {
        "payload_input": pi,
        "payload_output": {
            "mode": "matching",
            "candidats": [
                {
                    "z": z,
                    "nb_etiq_par_tour": n,
                    "circonference_mm": "425.45",
                    "pas_mm": "42.545",
                    "intervalle_mm": "2.545",
                    "nb_etiq_par_metre": 23,
                    "postes": [
                        {
                            "poste_numero": i,
                            "libelle": f"P{i}",
                            "montant_eur": "100.00",
                            "details": {},
                        }
                        for i in range(1, 8)
                    ],
                    "cout_revient_eur": "1228.04",
                    "pct_marge_appliquee": "0.18",
                    "prix_vente_ht_eur": "1449.09",
                    "prix_au_mille_eur": "7.00",
                }
                for z, n in [(134, 10), (121, 9), (108, 8)]
            ],
        },
        "cylindre_choisi_z": 134,
        "cylindre_choisi_nb_etiq": 10,
    }


# ---------------------------------------------------------------------------
# POST /api/devis — création
# ---------------------------------------------------------------------------


def test_post_devis_v1a_manuel_returns_201_and_full_detail():
    response = client.post("/api/devis", json=_payload_v1a_manuel())
    assert response.status_code == 201
    data = response.json()
    assert data["numero"].startswith(f"DEV-{datetime.now().year}-")
    assert data["statut"] == "brouillon"  # default
    assert data["mode_calcul"] == "manuel"
    assert Decimal(data["ht_total_eur"]) == Decimal("1449.09")
    assert Decimal(data["format_h_mm"]) == Decimal("40.00")
    assert Decimal(data["format_l_mm"]) == Decimal("60.00")
    assert data["machine_id"] == 1
    assert data["machine_nom"] == "Mark Andy P5"
    assert data["client_id"] is None
    assert data["client_nom"] is None
    # payload JSON correctement persisté + relu
    assert data["payload_input"]["mode_calcul"] == "manuel"
    assert data["payload_output"]["prix_vente_ht_eur"] == "1449.09"


def test_post_devis_v1a_matching_returns_201_with_cylindre_choisi():
    response = client.post("/api/devis", json=_payload_v1a_matching())
    assert response.status_code == 201
    data = response.json()
    assert data["mode_calcul"] == "matching"
    assert data["cylindre_choisi_z"] == 134
    assert data["cylindre_choisi_nb_etiq"] == 10
    # HT extrait du 1er candidat
    assert Decimal(data["ht_total_eur"]) == Decimal("1449.09")


def test_post_devis_numero_sequentiel_yearly():
    """Vérification numérotation séquentielle DEV-YYYY-0001 → 0002 → 0003."""
    annee = datetime.now().year
    for i in range(1, 4):
        r = client.post("/api/devis", json=_payload_v1a_manuel())
        assert r.status_code == 201
        assert r.json()["numero"] == f"DEV-{annee}-{i:04d}"


def test_post_devis_payload_invalide_returns_422():
    """payload_input sans format_etiquette_hauteur_mm → 422 (KeyError converted)."""
    bad = _payload_v1a_manuel()
    bad["payload_input"].pop("format_etiquette_hauteur_mm")
    r = client.post("/api/devis", json=bad)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/devis — liste paginée
# ---------------------------------------------------------------------------


def test_get_devis_list_returns_pagination_envelope():
    for _ in range(3):
        client.post("/api/devis", json=_payload_v1a_manuel())
    r = client.get("/api/devis?per_page=2")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["pages"] == 2
    assert len(data["items"]) == 2
    # Tri date_desc par défaut → premier item = dernier créé
    assert data["items"][0]["machine_nom"] == "Mark Andy P5"


def test_get_devis_list_filter_by_statut():
    r1 = client.post("/api/devis", json=_payload_v1a_manuel())
    devis1_id = r1.json()["id"]
    client.put(f"/api/devis/{devis1_id}", json={"statut": "valide"})
    client.post("/api/devis", json=_payload_v1a_manuel())  # brouillon

    r = client.get("/api/devis?statut=valide")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == devis1_id


def test_get_devis_list_search_by_numero():
    r1 = client.post("/api/devis", json=_payload_v1a_manuel())
    numero = r1.json()["numero"]
    client.post("/api/devis", json=_payload_v1a_manuel())

    r = client.get(f"/api/devis?search={numero}")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["numero"] == numero


def test_get_devis_list_empty():
    r = client.get("/api/devis")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["pages"] == 1


# ---------------------------------------------------------------------------
# GET /api/devis/{id} — détail
# ---------------------------------------------------------------------------


def test_get_devis_detail_returns_full_payload():
    r1 = client.post("/api/devis", json=_payload_v1a_manuel())
    devis_id = r1.json()["id"]

    r = client.get(f"/api/devis/{devis_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == devis_id
    assert "payload_input" in data
    assert "payload_output" in data
    assert "date_modification" in data


def test_get_devis_detail_404():
    r = client.get("/api/devis/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/devis/{id} — update
# ---------------------------------------------------------------------------


def test_put_devis_update_statut_only():
    r1 = client.post("/api/devis", json=_payload_v1a_manuel())
    devis_id = r1.json()["id"]
    r = client.put(f"/api/devis/{devis_id}", json={"statut": "valide"})
    assert r.status_code == 200
    assert r.json()["statut"] == "valide"


def test_put_devis_404():
    r = client.put("/api/devis/999999", json={"statut": "valide"})
    assert r.status_code == 404


def test_put_devis_extra_field_rejected():
    """extra='forbid' sur DevisUpdate → champ inconnu rejeté en 422."""
    r1 = client.post("/api/devis", json=_payload_v1a_manuel())
    devis_id = r1.json()["id"]
    r = client.put(f"/api/devis/{devis_id}", json={"champ_inconnu": 42})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/devis/{id}
# ---------------------------------------------------------------------------


def test_delete_devis_returns_204_then_404():
    r1 = client.post("/api/devis", json=_payload_v1a_manuel())
    devis_id = r1.json()["id"]
    r = client.delete(f"/api/devis/{devis_id}")
    assert r.status_code == 204
    r2 = client.get(f"/api/devis/{devis_id}")
    assert r2.status_code == 404


def test_delete_devis_404():
    r = client.delete("/api/devis/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/devis/{id}/duplicate
# ---------------------------------------------------------------------------


def test_duplicate_devis_creates_new_with_brouillon_status():
    r1 = client.post("/api/devis", json=_payload_v1a_manuel())
    devis = r1.json()
    devis_id = devis["id"]
    # Marque le source comme valide pour vérifier que duplicate force brouillon
    client.put(f"/api/devis/{devis_id}", json={"statut": "valide"})

    r = client.post(f"/api/devis/{devis_id}/duplicate")
    assert r.status_code == 201
    nouveau = r.json()
    assert nouveau["id"] != devis_id
    assert nouveau["numero"] != devis["numero"]
    assert nouveau["statut"] == "brouillon"
    # Mêmes payloads et dénormalisés
    assert nouveau["payload_input"] == devis["payload_input"]
    assert Decimal(nouveau["ht_total_eur"]) == Decimal("1449.09")


def test_duplicate_devis_404():
    r = client.post("/api/devis/999999/duplicate")
    assert r.status_code == 404
