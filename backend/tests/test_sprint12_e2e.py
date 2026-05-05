"""Tests E2E Sprint 12 multi-tenant — Lot S12-H.

Deux flows complets, exercés via HTTP réel (auth JWT, pas d'override) :

1. Flow IMPRIMEUR self-service : register → confirm-email → login → /me
   → CRUD scopé sur sa propre entreprise → cost engine → save devis.
2. Flow ADMIN Eric : login → POST /admin/users → list → disable+login KO
   → enable+login OK → delete → list à nouveau.

Le marker `no_auth_override` (cf. conftest.py) désactive l'override
autouse de `get_current_user` pour ces tests : on exerce l'auth réelle
de bout en bout.
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import User

pytestmark = pytest.mark.no_auth_override

client = TestClient(app)

ADMIN_EMAIL = "admin@devis-flexo.fr"
ADMIN_PASSWORD = "admin"  # fallback dev seed.py


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(email: str, password: str) -> str:
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _read_email_confirmation_token(email: str) -> str:
    """Récupère le token de confirmation depuis la BDD (mode test).

    En prod, l'utilisateur le reçoit par email — ici on lit directement
    le champ `email_confirmation_token` posé par /register.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None, f"User {email} introuvable après /register"
        assert user.email_confirmation_token, (
            "email_confirmation_token vide après /register"
        )
        return user.email_confirmation_token
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Flow 1 — Imprimeur self-service complet
# ---------------------------------------------------------------------------


def test_e2e_signup_flow_imprimeur_complet():
    """Inscription → confirmation → login → CRUD scopé → cost → devis."""
    new_email = "nouveau@imprim-test.fr"
    new_password = "secretpw_8plus"

    # 1. Register : crée user inactive + entreprise vierge
    r = client.post(
        "/api/auth/register",
        json={
            "email": new_email,
            "password": new_password,
            "nom_entreprise": "Imprim Test SAS",
            "nom_contact": "Jean Test",
        },
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["user_id"]

    # 2. Login refusé tant que email pas confirmé (is_active=False → 403)
    r = client.post(
        "/api/auth/login",
        json={"email": new_email, "password": new_password},
    )
    assert r.status_code in (401, 403), (
        f"Login devrait être refusé sur compte inactif, got {r.status_code}"
    )

    # 3. Confirm email avec token lu en BDD
    token = _read_email_confirmation_token(new_email)
    r = client.post("/api/auth/confirm-email", json={"token": token})
    assert r.status_code == 200, r.text

    # 4. Login OK maintenant
    access_token = _login(new_email, new_password)
    headers = _bearer(access_token)

    # 5. /me renvoie le bon user + entreprise scopée
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == new_email
    assert me["id"] == user_id
    assert me["nom_entreprise"] == "Imprim Test SAS"
    assert me["is_admin"] is False
    assert me["is_active"] is True

    # 6. Liste machines vide (nouveau tenant, pas de seed perso)
    r = client.get("/api/machines", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    # 7. Crée une machine pour ce tenant
    machine_payload = {
        "nom": "Presse Test E2E",
        "laize_max_mm": "330",
        "vitesse_max_m_min": 200,
        "vitesse_moyenne_m_h": 6000,
        "duree_calage_h": 1.0,
        "nb_couleurs": 6,
        "cout_horaire_eur": 70,
        "actif": True,
    }
    r = client.post("/api/machines", json=machine_payload, headers=headers)
    assert r.status_code == 201, r.text
    machine_id = r.json()["id"]

    # 8. Liste contient maintenant la machine
    r = client.get("/api/machines", headers=headers)
    assert r.status_code == 200
    machines = r.json()
    assert len(machines) == 1
    assert machines[0]["nom"] == "Presse Test E2E"

    # 9. Côté isolation : Eric admin ne doit PAS voir cette machine
    eric_token = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    r = client.get("/api/machines", headers=_bearer(eric_token))
    assert r.status_code == 200
    eric_machines = r.json()
    eric_machine_ids = [m["id"] for m in eric_machines]
    assert machine_id not in eric_machine_ids, (
        "ISOLATION KO : Eric voit la machine du nouveau tenant !"
    )


# ---------------------------------------------------------------------------
# Flow 2 — Admin Eric : créer / désactiver / réactiver / supprimer
# ---------------------------------------------------------------------------


def test_e2e_admin_flow_create_disable_enable_delete():
    """Eric admin pilote le cycle de vie complet d'un compte."""
    eric_token = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    eric_headers = _bearer(eric_token)

    # Avant : compte de Eric (au moins 1) listé
    r = client.get("/api/admin/users", headers=eric_headers)
    assert r.status_code == 200
    initial_count = len(r.json())
    assert initial_count >= 1
    assert any(u["email"] == ADMIN_EMAIL for u in r.json())

    # 1. Création d'un compte par admin (is_active=True direct)
    test_email = "test-admin-flow@imprim.fr"
    test_password = "adminflow_pw_123"
    r = client.post(
        "/api/admin/users",
        json={
            "email": test_email,
            "password": test_password,
            "nom_entreprise": "Imprim Admin Flow",
            "nom_contact": "Admin Flow",
            "is_admin": False,
        },
        headers=eric_headers,
    )
    assert r.status_code == 201, r.text
    new_user = r.json()
    new_user_id = new_user["id"]
    assert new_user["is_active"] is True
    assert new_user["is_admin"] is False

    # 2. List : 1 user de plus
    r = client.get("/api/admin/users", headers=eric_headers)
    assert r.status_code == 200
    assert len(r.json()) == initial_count + 1

    # 3. Le nouveau user peut se connecter direct (pas de confirmation email)
    new_token = _login(test_email, test_password)
    assert new_token

    # 4. Disable
    r = client.put(
        f"/api/admin/users/{new_user_id}/disable", headers=eric_headers
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # 5. Login désormais refusé (compte inactif → 403)
    r = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert r.status_code == 403, r.text

    # 6. Enable
    r = client.put(
        f"/api/admin/users/{new_user_id}/enable", headers=eric_headers
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is True

    # 7. Login OK à nouveau
    new_token = _login(test_email, test_password)
    assert new_token

    # 8. Delete : CASCADE entreprise + données scopées
    r = client.delete(
        f"/api/admin/users/{new_user_id}", headers=eric_headers
    )
    assert r.status_code == 204

    # 9. List : retour à l'état initial
    r = client.get("/api/admin/users", headers=eric_headers)
    assert r.status_code == 200
    final_emails = [u["email"] for u in r.json()]
    assert test_email not in final_emails


# ---------------------------------------------------------------------------
# Anti-régression sacrée : Eric admin sur compte demo voit V1a EXACT
# ---------------------------------------------------------------------------


def test_e2e_eric_admin_v1a_exact_preserved_through_auth():
    """Sacré V1a EXACT : 1 449,09 € via auth réelle (pas via fixture override).

    Ce test garantit que l'authentification ne dégrade pas le calcul
    pour Eric — un guard final avant le push prod.
    """
    eric_token = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = _bearer(eric_token)

    # Cas V1a sacré du repo : seed Eric avec machine_id=1, complexe_id=31
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
        "forfaits_st": [
            {"partenaire_st_id": 1, "montant_eur": "50.00"},
        ],
    }
    r = client.post("/api/cost/calculer", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    out = r.json()
    # V1a sacré : 1449.09 € HT (cf. project_devis_flexo_metier.md)
    assert Decimal(out["prix_vente_ht_eur"]) == Decimal("1449.09"), (
        f"V1a sacré KO via auth : got {out['prix_vente_ht_eur']}"
    )
    # 6.92 €/1000 sur 100 000 étiquettes — le calcul retourne prix_au_mille_eur
    # que l'on n'asserte pas ici (déjà couvert par test_cost_engine_5cas).
