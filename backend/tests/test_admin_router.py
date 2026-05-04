"""Tests intégration HTTP /api/admin (Sprint 12 Lot S12-D).

Le compte admin demo (entreprise_id=1, is_admin=True) est injecté par la
fixture autouse `seed_db_before_each_test`. Pour les cas "user normal
reçoit 403", on bascule l'override `get_current_user` sur user B
(is_admin=False par défaut depuis _ensure_user_b).
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.dependencies import get_current_user
from app.main import app
from app.models import Entreprise, User

client = TestClient(app)


def _user_b_not_admin():
    """Helper : retourne user B mais en forçant is_admin=False (cas test 403)."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "user.b@isolation-test.fr").first()
        if user is None:
            raise RuntimeError("User B introuvable — _ensure_user_b non appelé ?")
        # Force is_admin=False même si _ensure_user_b a posé True
        user.is_admin = False
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------


def test_admin_list_users_returns_all():
    """Admin Eric voit tous les users (au moins le sien)."""
    r = client.get("/api/admin/users")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Le compte demo doit être présent
    emails = [u["email"] for u in data]
    assert "admin@devis-flexo.fr" in emails
    # Les champs joints doivent être présents
    demo = next(u for u in data if u["email"] == "admin@devis-flexo.fr")
    assert demo["nom_entreprise"]  # non vide
    assert demo["is_demo"] is True
    assert demo["is_admin"] is True
    assert demo["is_active"] is True


def test_admin_list_users_unauthorized_for_normal_user(as_user_b):
    """User normal (is_admin=False) → 403 sur tous les endpoints admin."""
    # `as_user_b` met is_admin=True par défaut (cf. _ensure_user_b). On force False.
    app.dependency_overrides[get_current_user] = _user_b_not_admin
    r = client.get("/api/admin/users")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/admin/users
# ---------------------------------------------------------------------------


def test_admin_create_user_atomic_entreprise_and_user():
    """Création OK : Entreprise + User créés dans la même transaction."""
    payload = {
        "email": "nouveau@flexo-test.fr",
        "password": "secret_password_8plus",
        "nom_entreprise": "Imprimerie Nouvelle",
        "nom_contact": "Jean Nouvel",
        "is_admin": False,
    }
    r = client.post("/api/admin/users", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == "nouveau@flexo-test.fr"
    assert data["nom_entreprise"] == "Imprimerie Nouvelle"
    assert data["is_admin"] is False
    assert data["is_active"] is True
    assert data["is_demo"] is False
    # Vérifier l'entreprise est bien en BDD
    with SessionLocal() as db:
        ent = db.get(Entreprise, data["entreprise_id"])
        assert ent is not None
        assert ent.raison_sociale == "Imprimerie Nouvelle"


def test_admin_create_user_duplicate_email_returns_409():
    """L'email du compte demo (admin@devis-flexo.fr) existe déjà → 409."""
    payload = {
        "email": "admin@devis-flexo.fr",
        "password": "anotherpass123",
        "nom_entreprise": "Doublon",
        "nom_contact": "Doublon Test",
    }
    r = client.post("/api/admin/users", json=payload)
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# PUT /api/admin/users/{id}/disable et /enable
# ---------------------------------------------------------------------------


def test_admin_disable_then_enable_toggles_is_active():
    """Disable → is_active=False, Enable → is_active=True."""
    # Crée d'abord un user pour pouvoir le toggle (on évite de toucher au demo)
    create_payload = {
        "email": "toggle@flexo-test.fr",
        "password": "togglepass123",
        "nom_entreprise": "Toggle SARL",
        "nom_contact": "Toggle Contact",
    }
    r = client.post("/api/admin/users", json=create_payload)
    assert r.status_code == 201
    user_id = r.json()["id"]

    # Disable
    r = client.put(f"/api/admin/users/{user_id}/disable")
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # Enable
    r = client.put(f"/api/admin/users/{user_id}/enable")
    assert r.status_code == 200
    assert r.json()["is_active"] is True


def test_admin_disable_self_returns_403():
    """Eric ne peut pas se désactiver lui-même."""
    with SessionLocal() as db:
        admin_id = db.query(User).filter(
            User.email == "admin@devis-flexo.fr"
        ).first().id
    r = client.put(f"/api/admin/users/{admin_id}/disable")
    assert r.status_code == 403


def test_admin_disable_unknown_user_returns_404():
    r = client.put("/api/admin/users/99999/disable")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/admin/users/{id}
# ---------------------------------------------------------------------------


def test_admin_delete_user_cascade_removes_entreprise():
    """Supprimer un user supprime l'Entreprise via CASCADE ondelete."""
    # Crée un user avec entreprise dédiée
    payload = {
        "email": "tobe-deleted@flexo-test.fr",
        "password": "deletepass123",
        "nom_entreprise": "À Supprimer SARL",
        "nom_contact": "Delete Contact",
    }
    r = client.post("/api/admin/users", json=payload)
    assert r.status_code == 201
    user_id = r.json()["id"]
    entreprise_id = r.json()["entreprise_id"]

    # Delete
    r = client.delete(f"/api/admin/users/{user_id}")
    assert r.status_code == 204

    # Vérifier en BDD : User et Entreprise supprimés
    with SessionLocal() as db:
        assert db.get(User, user_id) is None
        assert db.get(Entreprise, entreprise_id) is None


def test_admin_cannot_delete_self():
    """Eric ne peut pas se suicider — protection produit."""
    with SessionLocal() as db:
        admin_id = db.query(User).filter(
            User.email == "admin@devis-flexo.fr"
        ).first().id
    r = client.delete(f"/api/admin/users/{admin_id}")
    assert r.status_code == 403
    assert "propre compte" in r.json()["detail"].lower()


def test_admin_cannot_delete_demo_account(as_user_b):
    """Le compte demo (is_demo=True) est sacré.

    On bascule sur user B (autre admin) pour pouvoir tenter de cibler
    le compte demo sans déclencher la garde 'propre compte'.
    """
    with SessionLocal() as db:
        demo = db.query(User).filter(
            User.email == "admin@devis-flexo.fr"
        ).first()
        demo_id = demo.id
    r = client.delete(f"/api/admin/users/{demo_id}")
    assert r.status_code == 403
    assert "demo" in r.json()["detail"].lower()


def test_admin_delete_unknown_user_returns_404():
    r = client.delete("/api/admin/users/99999")
    assert r.status_code == 404
