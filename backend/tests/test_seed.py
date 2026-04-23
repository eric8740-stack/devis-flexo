from app.db import SessionLocal
from app.models import Client, Entreprise, Fournisseur
from scripts.seed import run_seed


def test_seed_returns_expected_counts():
    counts = run_seed()
    assert counts == {"entreprise": 1, "client": 20, "fournisseur": 5}


def test_seed_persists_in_database():
    run_seed()
    with SessionLocal() as session:
        assert session.query(Entreprise).count() == 1
        assert session.query(Client).count() == 20
        assert session.query(Fournisseur).count() == 5


def test_seed_is_idempotent():
    run_seed()
    counts = run_seed()
    assert counts == {"entreprise": 1, "client": 20, "fournisseur": 5}
    with SessionLocal() as session:
        assert session.query(Client).count() == 20
