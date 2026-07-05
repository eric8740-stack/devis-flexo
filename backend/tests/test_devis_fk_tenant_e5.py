"""Tests blindage pilote E5 (audit 05/07/2026) — IDOR create/update devis.

Bug corrigé : create_devis / update_devis inséraient client_id (et, par
lot, machine_id / matiere_id / cylindre_id) sans vérifier l'appartenance
au tenant — un tenant pouvait rattacher son devis au client d'un autre et
lire des noms cross-tenant via _attach_relation_names.

Contrat : 404 anti-énumération (même comportement que scope_service),
jamais 403 ni 500.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Client
from tests.test_creation_devis_calcule_prix_aggregate import _fks_tenant1

client = TestClient(app)


def _id_client_demo() -> int:
    with SessionLocal() as db:
        c = db.query(Client).filter(Client.entreprise_id == 1).first()
        assert c is not None
        return c.id


def _payload_legacy(machine_id: int, client_id: int | None) -> dict:
    """Devis mono-config minimal (sans lots)."""
    return {
        "statut": "brouillon",
        "client_id": client_id,
        "payload_input": {
            "mode_calcul": "manuel",
            "machine_id": machine_id,
            "format_etiquette_hauteur_mm": 60,
            "format_etiquette_largeur_mm": 40,
        },
        "payload_output": {"mode": "manuel", "prix_vente_ht_eur": "100.00"},
    }


def _creer_machine_b() -> int:
    """Crée une machine pour le tenant courant (B) via l'API."""
    r = client.post(
        "/api/machines", json={"nom": "Presse E5 B", "laize_max_mm": 330}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_create_devis_avec_client_d_un_autre_tenant_404(switch_to_user_b):
    """Tenant B crée un devis avec le client_id du tenant A → 404."""
    client_a_id = _id_client_demo()
    switch_to_user_b()
    machine_b_id = _creer_machine_b()

    r = client.post(
        "/api/devis", json=_payload_legacy(machine_b_id, client_a_id)
    )
    assert r.status_code == 404, r.text
    assert "client" in r.json()["detail"].lower()

    # Contrôle : même payload SANS le client étranger → 201 (le 404 venait
    # bien de la validation FK tenant).
    r = client.post("/api/devis", json=_payload_legacy(machine_b_id, None))
    assert r.status_code == 201, r.text


def test_create_devis_avec_machine_d_un_autre_tenant_404(switch_to_user_b):
    """payload_input.machine_id (dénormalisé sur devis.machine_id) est
    aussi validé : machine du tenant A → 404 pour B."""
    machine_a_id, _, _ = _fks_tenant1()
    switch_to_user_b()

    r = client.post("/api/devis", json=_payload_legacy(machine_a_id, None))
    assert r.status_code == 404, r.text
    assert "machine" in r.json()["detail"].lower()


def test_create_devis_lots_avec_fk_d_un_autre_tenant_404(switch_to_user_b):
    """Devis multi-lots : cylindre/matière du tenant A dans un lot → 404."""
    machine_a_id, cyl_a_id, mat_a_id = _fks_tenant1()
    switch_to_user_b()
    machine_b_id = _creer_machine_b()

    payload = _payload_legacy(machine_b_id, None)
    payload["quantite_totale"] = 1000
    payload["lots"] = [
        {
            "cylindre_id": cyl_a_id,
            "machine_id": machine_b_id,
            "nb_poses_dev": 2,
            "nb_poses_laize": 3,
            "sens_enroulement": 1,
            "quantite": 1000,
            "matiere_id": mat_a_id,
        }
    ]

    r = client.post("/api/devis", json=payload)
    assert r.status_code == 404, r.text


def test_update_devis_avec_client_d_un_autre_tenant_404(switch_to_user_b):
    """PUT : rattacher un devis B au client du tenant A → 404, et le devis
    reste intact."""
    client_a_id = _id_client_demo()
    switch_to_user_b()
    machine_b_id = _creer_machine_b()

    r = client.post("/api/devis", json=_payload_legacy(machine_b_id, None))
    assert r.status_code == 201, r.text
    devis_b_id = r.json()["id"]

    r = client.put(
        f"/api/devis/{devis_b_id}", json={"client_id": client_a_id}
    )
    assert r.status_code == 404, r.text

    r = client.get(f"/api/devis/{devis_b_id}")
    assert r.status_code == 200
    assert r.json()["client_id"] is None
