"""Tests d'isolation multi-tenant Sprint 12 Lot S12-C.

Vérifient qu'un user d'une entreprise B ne voit pas / ne peut pas
modifier les ressources d'une entreprise A. Le code 404 (anti-enumeration)
est attendu plutôt que 403, conformément au brief S12-C §5.4.

Couvre les principales surfaces : client, machine, complexe, devis,
tarif_poste (read scoped) + cost engine (validate IDs).

La fixture `as_user_b` (conftest.py) bascule l'override `get_current_user`
sur un user B (entreprise_id=2). Le `seed_db_before_each_test` autouse
réinitialise tout entre chaque test, donc l'override admin reprend après.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Client, Devis, Machine

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _id_first_client_demo() -> int:
    """Renvoie l'id d'un client de l'entreprise demo (entreprise_id=1)."""
    with SessionLocal() as db:
        c = db.query(Client).filter(Client.entreprise_id == 1).first()
        assert c is not None, "Seed n'a pas créé de client pour entreprise_id=1"
        return c.id


def _id_first_machine_demo() -> int:
    with SessionLocal() as db:
        m = db.query(Machine).filter(Machine.entreprise_id == 1).first()
        assert m is not None, "Seed n'a pas créé de machine pour entreprise_id=1"
        return m.id


def _create_devis_demo() -> int:
    """Crée un devis V1a manuel pour entreprise demo via l'API et retourne son id."""
    payload = {
        "statut": "brouillon",
        "client_id": None,
        "payload_input": {
            "mode_calcul": "manuel",
            "machine_id": 1,
            "complexe_id": 31,
            "laize_utile_mm": 220,
            "ml_total": 3000,
            "format_etiquette_hauteur_mm": 60,
            "format_etiquette_largeur_mm": 40,
            "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
            "outil_decoupe_existant": True,
            "forfaits_st": [],
        },
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "1228.04",
            "pct_marge_appliquee": "0.18",
            "postes": [
                {"poste_numero": i, "libelle": f"P{i}", "montant_eur": "100.00", "details": {}}
                for i in range(1, 8)
            ],
        },
        "cylindre_choisi_z": None,
        "cylindre_choisi_nb_etiq": None,
    }
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Lectures : user B ne VOIT pas les ressources de A
# ---------------------------------------------------------------------------


def test_isolation_user_b_list_clients_returns_empty(as_user_b):
    """Demo a 1+ clients seedés. User B (entreprise vide) doit voir 0 client."""
    r = client.get("/api/clients")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_machines_returns_empty(as_user_b):
    r = client.get("/api/machines")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_complexes_returns_empty(as_user_b):
    r = client.get("/api/complexes")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_devis_returns_empty(as_user_b):
    r = client.get("/api/devis")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_isolation_user_b_list_outils_decoupe_returns_empty(as_user_b):
    r = client.get("/api/outils")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_partenaires_st_returns_empty(as_user_b):
    r = client.get("/api/partenaires-st")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_fournisseurs_returns_empty(as_user_b):
    r = client.get("/api/fournisseurs")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_charges_mensuelles_returns_empty(as_user_b):
    r = client.get("/api/charges-mensuelles")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_operations_finition_returns_empty(as_user_b):
    r = client.get("/api/operations-finition")
    assert r.status_code == 200
    assert r.json() == []


def test_isolation_user_b_list_catalogue_returns_empty(as_user_b):
    r = client.get("/api/catalogue")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# Détail / mutation : 404 (anti-enumeration) sur ressource d'A
# ---------------------------------------------------------------------------


def test_isolation_user_b_get_client_of_a_returns_404(as_user_b):
    client_a_id = _id_first_client_demo()
    r = client.get(f"/api/clients/{client_a_id}")
    assert r.status_code == 404


def test_isolation_user_b_delete_machine_of_a_returns_404(as_user_b):
    machine_a_id = _id_first_machine_demo()
    r = client.delete(f"/api/machines/{machine_a_id}")
    assert r.status_code == 404


def test_isolation_user_b_get_devis_of_a_returns_404(switch_to_user_b):
    """User A crée un devis, user B essaie de le lire → 404."""
    # Étape 1 : admin demo (override actif par autouse) crée le devis
    devis_a_id = _create_devis_demo()
    # Étape 2 : bascule sur user B (entreprise_id=2)
    switch_to_user_b()
    r = client.get(f"/api/devis/{devis_a_id}")
    assert r.status_code == 404


def test_isolation_user_b_duplicate_devis_of_a_returns_404(switch_to_user_b):
    devis_a_id = _create_devis_demo()
    switch_to_user_b()
    r = client.post(f"/api/devis/{devis_a_id}/duplicate")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Cost engine : IDs externes hors tenant → 404
# ---------------------------------------------------------------------------


def test_isolation_user_b_cost_calculer_with_machine_of_a_returns_404(as_user_b):
    """Machine 1 appartient à entreprise demo. User B → 404 sur calcul."""
    payload = {
        "mode_calcul": "manuel",
        "machine_id": 1,
        "complexe_id": 31,
        "laize_utile_mm": 220,
        "ml_total": 3000,
        "format_etiquette_hauteur_mm": 60,
        "format_etiquette_largeur_mm": 40,
        "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
        "outil_decoupe_existant": True,
        "forfaits_st": [],
    }
    r = client.post("/api/cost/calculer", json=payload)
    assert r.status_code == 404
    assert "machine" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tarif_poste : scope read (chaque entreprise a sa propre table seedée)
# ---------------------------------------------------------------------------


def test_isolation_user_b_list_tarifs_poste_returns_empty(as_user_b):
    """tarif_poste est scopé : user B (entreprise vierge) doit voir 0 paramètre."""
    r = client.get("/api/tarif-poste")
    assert r.status_code == 200
    body = r.json()
    # Body est un dict groupé par poste, on vérifie que tout est vide
    if isinstance(body, dict):
        for poste_params in body.values():
            assert poste_params == [] or len(poste_params) == 0
    else:
        assert body == []
