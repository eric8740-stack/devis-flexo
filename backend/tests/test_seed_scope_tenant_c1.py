"""Tests blindage pilote C1 (audit 05/07/2026) — seed scopé tenant démo.

Couvre :
  - run_seed ne détruit PAS les données d'un autre tenant (le bug C1 :
    DELETE globaux → suivre le README effaçait tous les comptes).
  - Le compte admin démo survit au re-seed (UPDATE, pas DELETE+INSERT) :
    même id → les sessions JWT actives restent valides.
  - Garde-fou PostgreSQL : refus sans --force-prod / SEED_CONFIRM_PROD=oui.
  - ADMIN_INITIAL_PASSWORD obligatoire quand la cible est PostgreSQL.
"""
import pytest

from app.db import SessionLocal
from app.models import Client, Entreprise, Machine, TarifEncre, User
from scripts.seed import (
    _resoudre_admin_password,
    _verifier_garde_fou_postgres,
    run_seed,
)

# Tenant secondaire jetable — nettoyé par conftest._reset_tenants_secondaires
# au test suivant.
TENANT_B_ID = 77


def _creer_tenant_b_avec_donnees() -> None:
    with SessionLocal() as db:
        db.add(
            Entreprise(
                id=TENANT_B_ID,
                raison_sociale="Imprimerie Pilote B",
                siret="00000000000077",
                email="contact@pilote-b.fr",
                is_demo=False,
            )
        )
        db.flush()
        db.add(
            Machine(
                entreprise_id=TENANT_B_ID,
                nom="Presse Pilote B",
                laize_max_mm=330,
            )
        )
        db.add(
            Client(
                entreprise_id=TENANT_B_ID,
                raison_sociale="Client du Pilote B",
            )
        )
        db.add(
            TarifEncre(
                entreprise_id=TENANT_B_ID,
                type_encre="pantone",
                libelle="Pantone pilote B",
                prix_kg_defaut=20,
            )
        )
        db.commit()


def test_re_seed_preserve_les_donnees_des_autres_tenants():
    """C1 — un re-seed ne touche QUE le tenant démo : l'entreprise B, sa
    machine, son client et son tarif encre survivent."""
    _creer_tenant_b_avec_donnees()

    run_seed()

    with SessionLocal() as db:
        assert db.get(Entreprise, TENANT_B_ID) is not None
        assert (
            db.query(Machine)
            .filter_by(entreprise_id=TENANT_B_ID, nom="Presse Pilote B")
            .count()
            == 1
        )
        assert (
            db.query(Client).filter_by(entreprise_id=TENANT_B_ID).count() == 1
        )
        assert (
            db.query(TarifEncre)
            .filter_by(entreprise_id=TENANT_B_ID, type_encre="pantone")
            .count()
            == 1
        )
        # Et le tenant démo est bien reparti d'un état propre (seed complet).
        assert db.query(Machine).filter_by(entreprise_id=1).count() == 3


def test_re_seed_preserve_le_user_admin_demo():
    """Le compte admin démo est UPDATE (pas recréé) : id stable entre deux
    re-seeds → sessions JWT actives préservées."""
    with SessionLocal() as db:
        user_avant = (
            db.query(User).filter(User.entreprise_id == 1).first()
        )
        assert user_avant is not None
        id_avant = user_avant.id

    run_seed()

    with SessionLocal() as db:
        user_apres = (
            db.query(User).filter(User.entreprise_id == 1).first()
        )
        assert user_apres is not None
        assert user_apres.id == id_avant


# ---------------------------------------------------------------------------
# Garde-fous PostgreSQL (unitaires — pas besoin d'un vrai Postgres)
# ---------------------------------------------------------------------------


def test_garde_fou_refuse_postgres_sans_confirmation(monkeypatch):
    monkeypatch.delenv("SEED_CONFIRM_PROD", raising=False)
    with pytest.raises(SystemExit, match="REFUS"):
        _verifier_garde_fou_postgres("postgresql", force=False)


def test_garde_fou_accepte_postgres_avec_force():
    _verifier_garde_fou_postgres("postgresql", force=True)  # ne lève pas


def test_garde_fou_accepte_postgres_avec_env(monkeypatch):
    monkeypatch.setenv("SEED_CONFIRM_PROD", "oui")
    _verifier_garde_fou_postgres("postgresql", force=False)  # ne lève pas


def test_garde_fou_no_op_sur_sqlite(monkeypatch):
    monkeypatch.delenv("SEED_CONFIRM_PROD", raising=False)
    _verifier_garde_fou_postgres("sqlite", force=False)  # ne lève pas


def test_admin_password_obligatoire_sur_postgres(monkeypatch):
    monkeypatch.delenv("ADMIN_INITIAL_PASSWORD", raising=False)
    with pytest.raises(SystemExit, match="ADMIN_INITIAL_PASSWORD"):
        _resoudre_admin_password("postgresql")


def test_admin_password_env_prioritaire(monkeypatch):
    monkeypatch.setenv("ADMIN_INITIAL_PASSWORD", "s3cret-pilote")
    assert _resoudre_admin_password("postgresql") == "s3cret-pilote"
    assert _resoudre_admin_password("sqlite") == "s3cret-pilote"


def test_admin_password_fallback_dev_sqlite(monkeypatch):
    monkeypatch.delenv("ADMIN_INITIAL_PASSWORD", raising=False)
    assert _resoudre_admin_password("sqlite") == "admin"
