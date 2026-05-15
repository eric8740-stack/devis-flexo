"""Tests du middleware `require_module` (Sprint 13 Lot S13.A).

Vérifie l'activation modulaire FlexoSuite :
- 200 quand le user a le module activé
- 403 explicite quand le module n'est pas activé
- bypass admin (Eric is_admin=True) qui garde l'accès à tout
- ValueError au boot si on protège une route avec un nom de module invalide
- Schéma UserMe expose bien les flags has_flexocompare / has_flexocheck

Ces tests sont indépendants du moteur de coûts existant : on déclare des
routes éphémères dans une instance FastAPI test pour exercer uniquement
le middleware en isolation.
"""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.dependencies import (
    SUPPORTED_MODULES,
    get_current_user,
    require_module,
)
from app.main import app as main_app
from app.models import User


# ---------------------------------------------------------------------------
# Helpers — mini app FastAPI dédiée pour exercer le middleware en isolation
# ---------------------------------------------------------------------------


def _build_test_app() -> tuple[FastAPI, TestClient]:
    """Construit une app FastAPI minimale avec 2 routes protégées par chacun
    des modules. On override `get_current_user` dans chaque test pour
    simuler différents profils utilisateur sans toucher à la BDD.
    """
    test_app = FastAPI()

    @test_app.get("/_protected/compare")
    def route_compare(user: User = Depends(require_module("flexocompare"))):
        return {"module": "flexocompare", "user_email": user.email}

    @test_app.get("/_protected/check")
    def route_check(user: User = Depends(require_module("flexocheck"))):
        return {"module": "flexocheck", "user_email": user.email}

    return test_app, TestClient(test_app)


def _make_user(
    *,
    is_admin: bool = False,
    has_flexocompare: bool = True,
    has_flexocheck: bool = True,
) -> User:
    """User SQLAlchemy non persisté — suffisant car require_module ne fait
    que lire les attributs du user retourné par `get_current_user`.
    """
    return User(
        id=999,
        email="middleware-test@flexosuite.fr",
        password_hash="x",
        nom_contact="Middleware Test",
        entreprise_id=999,
        is_active=True,
        is_admin=is_admin,
        has_flexocompare=has_flexocompare,
        has_flexocheck=has_flexocheck,
    )


# ---------------------------------------------------------------------------
# Tests du middleware require_module
# ---------------------------------------------------------------------------


def test_require_module_accepts_user_with_flag_true():
    """User non-admin avec has_flexocompare=True → 200 sur /compare."""
    test_app, client = _build_test_app()
    user = _make_user(has_flexocompare=True, has_flexocheck=False)
    test_app.dependency_overrides[get_current_user] = lambda: user

    r = client.get("/_protected/compare")
    assert r.status_code == 200
    assert r.json()["module"] == "flexocompare"


def test_require_module_rejects_user_with_flag_false():
    """User non-admin avec has_flexocheck=False → 403 sur /check, message clair."""
    test_app, client = _build_test_app()
    user = _make_user(has_flexocompare=True, has_flexocheck=False)
    test_app.dependency_overrides[get_current_user] = lambda: user

    r = client.get("/_protected/check")
    assert r.status_code == 403
    # Le message doit mentionner explicitement le module manquant pour aider
    # le frontend à afficher un upsell ciblé.
    assert "flexocheck" in r.json()["detail"].lower()


def test_require_module_admin_bypass():
    """User admin sans le flag → accès quand même (override pour support Eric)."""
    test_app, client = _build_test_app()
    # Admin Eric avec AUCUN module activé : doit quand même passer.
    admin = _make_user(
        is_admin=True, has_flexocompare=False, has_flexocheck=False
    )
    test_app.dependency_overrides[get_current_user] = lambda: admin

    r_compare = client.get("/_protected/compare")
    r_check = client.get("/_protected/check")
    assert r_compare.status_code == 200
    assert r_check.status_code == 200


def test_require_module_rejects_invalid_module_name_at_boot():
    """Si un router tente require_module('flexbidon'), ValueError au démarrage.

    Garde-fou anti-faute-de-frappe : on échoue à l'enregistrement de la
    route plutôt qu'à la première requête en prod.
    """
    import pytest

    with pytest.raises(ValueError, match="non support"):
        require_module("flexbidon")


def test_supported_modules_set_is_frozen():
    """SUPPORTED_MODULES contient exactement les 2 modules Sprint 13."""
    assert SUPPORTED_MODULES == frozenset({"flexocompare", "flexocheck"})


# ---------------------------------------------------------------------------
# Tests intégration sur la vraie app : /api/auth/me expose les flags
# ---------------------------------------------------------------------------


def test_api_auth_me_exposes_module_flags():
    """L'endpoint /api/auth/me doit renvoyer has_flexocompare + has_flexocheck.

    On utilise l'override autouse (admin demo) configuré par conftest →
    l'admin Eric a les 2 flags à True (bundle FlexoSuite).
    """
    client = TestClient(main_app)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["has_flexocompare"] is True
    assert body["has_flexocheck"] is True


def test_user_compare_only_has_correct_flags(as_user_flexocompare_only):
    """La fixture as_user_flexocompare_only crée bien un user avec UN seul module."""
    client = TestClient(main_app)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["has_flexocompare"] is True
    assert body["has_flexocheck"] is False
    assert body["is_admin"] is False


def test_user_check_only_has_correct_flags(as_user_flexocheck_only):
    """La fixture as_user_flexocheck_only crée bien un user avec l'autre module."""
    client = TestClient(main_app)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["has_flexocompare"] is False
    assert body["has_flexocheck"] is True
    assert body["is_admin"] is False
