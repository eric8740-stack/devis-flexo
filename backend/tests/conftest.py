"""Conftest pytest — Sprint 12-C multi-tenant scoped.

Stratégie pour adapter ~30 fichiers tests existants SANS refactor massif :
au lieu d'ajouter un header Authorization sur chaque `TestClient`, on
override la dépendance `get_current_user` au niveau FastAPI via
`app.dependency_overrides`. Tous les endpoints scopés "voient" alors
le compte admin demo (entreprise_id=1) sans token réel.

- Tests classiques : autouse `seed_db_before_each_test` seede + override
  → tout ce qui était vert reste vert, le scope passe en transparence.
- Tests d'isolation : utilisent la fixture `as_user_b` (entreprise_id=2)
  pour vérifier qu'un user d'une autre entreprise reçoit bien 404.
"""
import pytest
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.dependencies import get_current_user
from app.main import app
from app.models import Entreprise, User
from app.services.auth_service import hash_password
from scripts.seed import run_seed

DEMO_ENTREPRISE_ID = 1
DEMO_ADMIN_EMAIL = "admin@devis-flexo.fr"

# Entreprise B : utilisée uniquement par les tests d'isolation S12-C.
USER_B_ENTREPRISE_ID = 2
USER_B_EMAIL = "user.b@isolation-test.fr"


def _get_demo_admin() -> User:
    """Retourne le User admin demo (entreprise_id=1) en BDD."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_ADMIN_EMAIL).first()
        if user is None:
            raise RuntimeError(
                f"Demo admin {DEMO_ADMIN_EMAIL} introuvable — seed cassé ?"
            )
        return user
    finally:
        db.close()


def _ensure_user_b() -> User:
    """Crée (idempotent) une 2e entreprise + user B pour les tests d'isolation.

    Appelée à la demande par la fixture `as_user_b`. Réutilise la session
    seedée — pas de re-seed nécessaire.
    """
    db: Session = SessionLocal()
    try:
        ent_b = db.query(Entreprise).filter(
            Entreprise.id == USER_B_ENTREPRISE_ID
        ).first()
        if ent_b is None:
            ent_b = Entreprise(
                id=USER_B_ENTREPRISE_ID,
                raison_sociale="Entreprise Isolation B",
                siret="00000000000002",
                email="contact@isolation-test.fr",
                is_demo=False,
            )
            db.add(ent_b)
            db.flush()

        user_b = db.query(User).filter(User.email == USER_B_EMAIL).first()
        if user_b is None:
            user_b = User(
                email=USER_B_EMAIL,
                password_hash=hash_password("test_b_pw"),
                nom_contact="User B Isolation",
                entreprise_id=USER_B_ENTREPRISE_ID,
                is_active=True,
                is_admin=True,
            )
            db.add(user_b)
        db.commit()
        db.refresh(user_b)
        return user_b
    finally:
        db.close()


def pytest_configure(config):
    """Déclare le marker `no_auth_override` (utilisé par les tests d'auth)."""
    config.addinivalue_line(
        "markers",
        "no_auth_override: ne pas appliquer l'override get_current_user "
        "(pour tests qui exercent l'auth réelle 401/403/JWT)",
    )


@pytest.fixture(autouse=True)
def seed_db_before_each_test(request):
    """Réinitialise la base seedée + auto-authentifie comme admin demo.

    Override `get_current_user` → retourne admin@devis-flexo.fr
    (entreprise_id=1). Les tests classiques voient tous leurs endpoints
    scopés sur l'entreprise demo, ce qui préserve le comportement
    pré-S12-C (où `entreprise_id=1` était hardcodé).

    Exception : les tests marqués `@pytest.mark.no_auth_override`
    (test_auth_router, test_auth_service) gardent l'auth réelle.
    """
    run_seed()
    if request.node.get_closest_marker("no_auth_override") is None:
        app.dependency_overrides[get_current_user] = _get_demo_admin
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def as_user_b():
    """Bascule l'override `get_current_user` sur le user B (entreprise_id=2).

    Usage tests d'isolation lecture :

        def test_user_b_voit_pas_clients_de_a(as_user_b):
            response = client.get("/api/clients")
            assert response.json() == []
    """
    user_b = _ensure_user_b()
    app.dependency_overrides[get_current_user] = lambda: _get_user_b_fresh()
    yield user_b
    # Le teardown autouse remet l'override admin pour le test suivant.


@pytest.fixture
def switch_to_user_b():
    """Renvoie une fonction qui bascule sur user B à la demande dans le test.

    Utile quand un test doit d'abord agir comme A (créer un devis), PUIS
    basculer comme B (vérifier que B reçoit 404).

    Usage :

        def test_isolation_devis(switch_to_user_b):
            devis_id = client.post(...).json()["id"]   # admin A
            switch_to_user_b()
            assert client.get(f"/api/devis/{devis_id}").status_code == 404
    """
    def _do_switch():
        _ensure_user_b()
        app.dependency_overrides[get_current_user] = lambda: _get_user_b_fresh()

    return _do_switch


def _get_user_b_fresh() -> User:
    """Récupère User B via une nouvelle session (évite DetachedInstanceError)."""
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == USER_B_EMAIL).first()
        if user is None:
            raise RuntimeError("User B introuvable — appeler `as_user_b` d'abord ?")
        return user
    finally:
        db.close()
