"""Tests intégration HTTP /api/auth — Sprint 12 Lot S12-B.

Le seed crée un compte admin Eric (email='admin@devis-flexo.fr',
password='admin', is_active=True, is_admin=True). On l'utilise pour
exercer login, /me, refresh et reset-password.

Les flux register + confirm-email sont testés sur des emails frais
(qui sont wipés à chaque test par la fixture `seed_db_before_each_test`
de conftest).
"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.db import SessionLocal
from app.main import app
from app.models import User
from app.services.auth_service import (
    JWT_ALGORITHM,
    JWT_SECRET,
    create_access_token,
)

client = TestClient(app)

ADMIN_EMAIL = "admin@devis-flexo.fr"
ADMIN_PASSWORD = "admin"  # fallback dev seed.py


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login_admin() -> dict:
    """Login admin + retourne le payload JSON {access_token, refresh_token, ...}."""
    r = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


def test_register_returns_201_and_creates_user_inactive():
    r = client.post(
        "/api/auth/register",
        json={
            "email": "newcomer@example.com",
            "password": "verysecret123",
            "nom_entreprise": "Imprimerie Newcomer",
            "nom_contact": "Alice Newcomer",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "newcomer@example.com"
    assert body["user_id"] > 1  # admin a id=1, les nouveaux sont >1

    # Vérifie en BDD : user créé, is_active=False, token confirmation présent
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "newcomer@example.com").first()
        assert user is not None
        assert user.is_active is False
        assert user.is_admin is False
        assert user.email_confirmation_token is not None
        assert user.email_confirmation_expires is not None
        # Entreprise associée créée avec siret placeholder
        assert user.entreprise is not None
        assert user.entreprise.raison_sociale == "Imprimerie Newcomer"
        assert user.entreprise.siret == "00000000000000"
        assert user.entreprise.is_demo is False


def test_register_duplicate_email_returns_409():
    """L'admin existe déjà — register avec son email doit échouer."""
    r = client.post(
        "/api/auth/register",
        json={
            "email": ADMIN_EMAIL,
            "password": "anotherpassword",
            "nom_entreprise": "Tentative duplication",
            "nom_contact": "Spammer",
        },
    )
    assert r.status_code == 409


def test_register_password_too_short_returns_422():
    r = client.post(
        "/api/auth/register",
        json={
            "email": "short@example.com",
            "password": "abc",  # < 8 chars
            "nom_entreprise": "X",
            "nom_contact": "Y",
        },
    )
    assert r.status_code == 422


def test_register_invalid_email_returns_422():
    r = client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "verysecret123",
            "nom_entreprise": "X",
            "nom_contact": "Y",
        },
    )
    assert r.status_code == 422


def test_register_extra_field_returns_422():
    """`extra="forbid"` rejette les champs accessoires."""
    r = client.post(
        "/api/auth/register",
        json={
            "email": "extra@example.com",
            "password": "verysecret123",
            "nom_entreprise": "X",
            "nom_contact": "Y",
            "is_admin": True,  # ← injection refused
        },
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_admin_returns_token_pair():
    body = _login_admin()
    assert "access_token" in body and body["access_token"].count(".") == 2
    assert "refresh_token" in body and body["refresh_token"].count(".") == 2
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600  # 60 min default


def test_login_unknown_email_returns_401():
    r = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "whatever"},
    )
    assert r.status_code == 401


def test_login_wrong_password_returns_401():
    r = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrongpassword"},
    )
    assert r.status_code == 401


def test_login_inactive_account_returns_403():
    """Crée un user inactif et tente login."""
    client.post(
        "/api/auth/register",
        json={
            "email": "inactive@example.com",
            "password": "verysecret123",
            "nom_entreprise": "Inactive Corp",
            "nom_contact": "Inactive",
        },
    )
    r = client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "verysecret123"},
    )
    assert r.status_code == 403


def test_login_updates_date_derniere_connexion():
    _login_admin()
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        assert admin is not None
        assert admin.date_derniere_connexion is not None


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


def test_me_without_token_returns_401():
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token_returns_401():
    r = client.get("/api/auth/me", headers=_bearer("not-a-jwt"))
    assert r.status_code == 401


def test_me_with_expired_token_returns_401():
    """Forge un token avec exp dans le passé."""
    expired_payload = {
        "sub": "1",
        "entreprise_id": 1,
        "type": "access",
        "iat": int((datetime.now(tz=timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(tz=timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    expired = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    r = client.get("/api/auth/me", headers=_bearer(expired))
    assert r.status_code == 401


def test_me_with_refresh_token_used_as_access_returns_401():
    """Refresh token consommé comme access → 401 (type mismatch)."""
    body = _login_admin()
    r = client.get("/api/auth/me", headers=_bearer(body["refresh_token"]))
    assert r.status_code == 401


def test_me_returns_user_info():
    body = _login_admin()
    r = client.get("/api/auth/me", headers=_bearer(body["access_token"]))
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == ADMIN_EMAIL
    assert me["nom_contact"] == "Eric Paysant"
    assert me["is_admin"] is True
    assert me["is_active"] is True
    assert me["entreprise_id"] == 1
    assert me["nom_entreprise"]  # raison sociale Paysant & Fils


# ---------------------------------------------------------------------------
# Logout (no-op)
# ---------------------------------------------------------------------------


def test_logout_returns_200():
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"detail": "Logged out"}


# ---------------------------------------------------------------------------
# Confirm email
# ---------------------------------------------------------------------------


def test_confirm_email_activates_user():
    # Register d'abord pour avoir un user inactif avec un token
    client.post(
        "/api/auth/register",
        json={
            "email": "confirm@example.com",
            "password": "verysecret123",
            "nom_entreprise": "Confirm Corp",
            "nom_contact": "Bob",
        },
    )
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "confirm@example.com").first()
        token = user.email_confirmation_token

    r = client.post("/api/auth/confirm-email", json={"token": token})
    assert r.status_code == 200

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "confirm@example.com").first()
        assert user.is_active is True
        assert user.email_confirmation_token is None
        assert user.email_confirmation_expires is None


def test_confirm_email_invalid_token_returns_400():
    r = client.post("/api/auth/confirm-email", json={"token": "invalidtoken1234567890"})
    assert r.status_code == 400


def test_confirm_email_expired_token_returns_400():
    # Crée un user avec un token expiré
    client.post(
        "/api/auth/register",
        json={
            "email": "expired@example.com",
            "password": "verysecret123",
            "nom_entreprise": "Expired Corp",
            "nom_contact": "Charlie",
        },
    )
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "expired@example.com").first()
        # Naive UTC pour cohérence SQLite + Postgres
        user.email_confirmation_expires = (
            datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        )
        token = user.email_confirmation_token
        db.commit()

    r = client.post("/api/auth/confirm-email", json={"token": token})
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Forgot + reset password
# ---------------------------------------------------------------------------


def test_forgot_password_known_email_returns_200_and_sets_token():
    r = client.post("/api/auth/forgot-password", json={"email": ADMIN_EMAIL})
    assert r.status_code == 200
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        assert admin.password_reset_token is not None
        assert admin.password_reset_expires is not None


def test_forgot_password_unknown_email_returns_200_anti_enum():
    """Anti-enumeration : on retourne 200 même pour email inconnu."""
    r = client.post(
        "/api/auth/forgot-password", json={"email": "ghost@example.com"}
    )
    assert r.status_code == 200


def test_reset_password_valid_token_changes_password():
    # Demande reset
    client.post("/api/auth/forgot-password", json={"email": ADMIN_EMAIL})
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        token = admin.password_reset_token

    # Reset
    r = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "newAdminPass456"},
    )
    assert r.status_code == 200

    # Login avec le nouveau password
    r = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "newAdminPass456"},
    )
    assert r.status_code == 200

    # L'ancien password ne marche plus
    r = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 401


def test_reset_password_invalid_token_returns_400():
    r = client.post(
        "/api/auth/reset-password",
        json={"token": "bogusbogusbogus123", "new_password": "newPassword42"},
    )
    assert r.status_code == 400


def test_reset_password_expired_token_returns_400():
    client.post("/api/auth/forgot-password", json={"email": ADMIN_EMAIL})
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        # Naive UTC
        admin.password_reset_expires = (
            datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
        )
        token = admin.password_reset_token
        db.commit()

    r = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "tryNewPassword1"},
    )
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


def test_refresh_returns_new_token_pair():
    body = _login_admin()
    r = client.post(
        "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert r.status_code == 200
    new_body = r.json()
    assert new_body["access_token"]
    assert new_body["refresh_token"]


def test_refresh_with_access_token_returns_401():
    """Access token consommé comme refresh → 401 (type mismatch)."""
    body = _login_admin()
    r = client.post(
        "/api/auth/refresh", json={"refresh_token": body["access_token"]}
    )
    assert r.status_code == 401


def test_refresh_with_invalid_token_returns_401():
    r = client.post(
        "/api/auth/refresh", json={"refresh_token": "not-a-jwt-1234567890"}
    )
    assert r.status_code == 401


def test_refresh_for_inactive_user_returns_401():
    """User désactivé après émission du refresh → refresh devient 401."""
    # Forge un refresh token pour un user désactivé
    from app.services.auth_service import create_refresh_token as _crt

    # Register inactive user
    client.post(
        "/api/auth/register",
        json={
            "email": "ref-inactive@example.com",
            "password": "verysecret123",
            "nom_entreprise": "Inactive Refresh",
            "nom_contact": "Dave",
        },
    )
    with SessionLocal() as db:
        u = db.query(User).filter(
            User.email == "ref-inactive@example.com"
        ).first()
        refresh = _crt(u.id, u.entreprise_id)

    r = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401
