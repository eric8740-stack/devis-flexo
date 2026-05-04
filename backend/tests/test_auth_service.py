"""Tests unitaires auth_service — Sprint 12 Lot S12-B.

Pas de DB ni de TestClient ici : on exerce uniquement les fonctions
pures (hash/verify, encode/decode JWT, génération tokens).
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.services import auth_service
from app.services.auth_service import (
    JWT_ALGORITHM,
    JWT_SECRET,
    AuthError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_random_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Hash + verify password
# ---------------------------------------------------------------------------


def test_hash_password_returns_bcrypt_string():
    h = hash_password("plain-password-123")
    # bcrypt commence toujours par $2b$ (ou $2a$/$2y$ selon les versions)
    assert h.startswith("$2") and len(h) >= 50


def test_hash_password_different_each_call():
    """Salt aléatoire → 2 hashes distincts pour le même password."""
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2


def test_verify_password_accepts_correct():
    h = hash_password("correct-pw-42")
    assert verify_password("correct-pw-42", h) is True


def test_verify_password_rejects_wrong():
    h = hash_password("correct-pw")
    assert verify_password("wrong-pw", h) is False


# ---------------------------------------------------------------------------
# JWT access + refresh
# ---------------------------------------------------------------------------


def test_create_access_token_returns_token_and_expires_in():
    token, expires_in = create_access_token(user_id=42, entreprise_id=7)
    assert isinstance(token, str) and token.count(".") == 2  # JWT 3 parts
    assert expires_in == 60 * 60  # default 60 min


def test_create_access_token_payload():
    token, _ = create_access_token(user_id=42, entreprise_id=7)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["entreprise_id"] == 7
    assert payload["type"] == "access"
    assert "iat" in payload and "exp" in payload


def test_create_refresh_token_payload():
    token = create_refresh_token(user_id=42, entreprise_id=7)
    payload = decode_token(token, expected_type="refresh")
    assert payload["type"] == "refresh"
    assert payload["sub"] == "42"


def test_decode_token_expired_raises():
    """Forge un token avec exp dans le passé → AuthError."""
    expired_payload = {
        "sub": "1",
        "entreprise_id": 1,
        "type": "access",
        "iat": int((datetime.now(tz=timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(tz=timezone.utc) - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    with pytest.raises(AuthError):
        decode_token(expired_token)


def test_decode_token_invalid_signature_raises():
    """Token signé avec un autre secret → AuthError."""
    fake = jwt.encode({"sub": "1"}, "another-secret", algorithm=JWT_ALGORITHM)
    with pytest.raises(AuthError):
        decode_token(fake)


def test_decode_token_wrong_type_raises():
    """Refresh token consommé comme access → AuthError."""
    refresh = create_refresh_token(user_id=1, entreprise_id=1)
    with pytest.raises(AuthError):
        decode_token(refresh, expected_type="access")


def test_decode_token_garbage_raises():
    with pytest.raises(AuthError):
        decode_token("not-a-jwt-at-all")


# ---------------------------------------------------------------------------
# Tokens random emails
# ---------------------------------------------------------------------------


def test_generate_random_token_unique_and_url_safe():
    a = generate_random_token()
    b = generate_random_token()
    assert a != b
    # URL-safe : alphabet limité à [A-Za-z0-9_-]
    assert all(c.isalnum() or c in "-_" for c in a)
    assert len(a) >= 40  # 32 bytes b64 = ~43 chars


def test_confirmation_email_expires_at_24h():
    """Expires retournés en UTC naive (cohérent SQLite + Postgres)."""
    expires = auth_service.confirmation_email_expires_at()
    delta = expires - datetime.now(tz=timezone.utc).replace(tzinfo=None)
    assert timedelta(hours=23, minutes=58) < delta <= timedelta(hours=24)


def test_password_reset_expires_at_1h():
    expires = auth_service.password_reset_expires_at()
    delta = expires - datetime.now(tz=timezone.utc).replace(tzinfo=None)
    assert timedelta(minutes=58) < delta <= timedelta(hours=1)
