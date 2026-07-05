"""Tests blindage pilote E3 (audit 05/07/2026) — fail-fast JWT_SECRET.

`_resolve_jwt_secret` doit REFUSER de démarrer (RuntimeError) quand
JWT_SECRET est absent en environnement de prod (heuristique : DATABASE_URL
Postgres OU RAILWAY_ENVIRONMENT défini). En dev local SQLite : fallback
conservé (avec WARNING) pour ne pas casser le confort dev.
"""
import pytest

from app.services.auth_service import _is_environnement_prod, _resolve_jwt_secret


@pytest.fixture(autouse=True)
def _env_propre(monkeypatch):
    """Neutralise les variables d'env qui pilotent l'heuristique."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)


def test_secret_env_prioritaire(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "un-secret-solide")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    assert _resolve_jwt_secret() == "un-secret-solide"


def test_refuse_sans_secret_si_database_url_postgres(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://user:pw@host:5432/railway"
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _resolve_jwt_secret()


def test_refuse_sans_secret_si_database_url_postgres_legacy(monkeypatch):
    # Railway/Heroku livrent parfois le scheme legacy `postgres://`.
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pw@host:5432/railway")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _resolve_jwt_secret()


def test_refuse_sans_secret_si_railway_environment(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _resolve_jwt_secret()


def test_fallback_dev_sqlite_conserve():
    """Dev local (pas de DATABASE_URL / SQLite) → fallback + pas d'erreur."""
    assert _resolve_jwt_secret() == "dev-secret-change-me"


def test_fallback_dev_database_url_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./devis_flexo.db")
    assert _resolve_jwt_secret() == "dev-secret-change-me"


def test_heuristique_prod():
    assert _is_environnement_prod() is False
