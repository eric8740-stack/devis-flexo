from app.db import SessionLocal
from app.models import Client, Entreprise, Fournisseur
from scripts.seed import run_seed


EXPECTED_COUNTS = {
    "entreprise": 1,
    "client": 20,
    "fournisseur": 5,
    "machine": 3,
    "operation_finition": 5,
    "partenaire_st": 4,
    "charge_mensuelle": 6,
    "complexe": 31,
    "catalogue": 5,
    # Sprint 3 Lot 3b — 5 tables paramétriques moteur v2
    # Sprint 9 v2 — 7 préexistants + 3 nouveaux outillage (Dette 1 migrée)
    "tarif_poste": 10,
    "tarif_encre": 5,
    "temps_operation_standard": 15,
    "correspondance_laize_metrage": 33,
    "charge_machine_mensuelle": 1,
    # Sprint 5 Lot 5a
    "outil_decoupe": 4,
}


def test_seed_returns_expected_counts():
    counts = run_seed()
    assert counts == EXPECTED_COUNTS


def test_seed_persists_in_database():
    run_seed()
    with SessionLocal() as session:
        assert session.query(Entreprise).count() == 1
        assert session.query(Client).count() == 20
        assert session.query(Fournisseur).count() == 5


def test_seed_is_idempotent():
    run_seed()
    counts = run_seed()
    assert counts == EXPECTED_COUNTS
    with SessionLocal() as session:
        assert session.query(Client).count() == 20
