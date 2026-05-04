"""Tests E2E mini-sprint Notes 15+16+bornes (04/05/2026).

Valident les 3 dettes résorbées :
- Note 15 : seed.py gère désormais la FK devis_machine_id_fkey
- Note 16 : auto-increment ids sur catalogues (sync séquences Postgres)
- Bornes élargies : PUT cliche_prix_couleur à 90 € passe (vs 60 € max avant)
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis
from scripts.seed import run_seed

client = TestClient(app)


def test_note_15_seed_after_devis_in_db_does_not_fail():
    """Note 15 : run_seed() doit fonctionner même si la table devis contient
    des lignes référençant `machine.id` via FK NOT NULL.

    Avant fix Lot M1 : `session.query(Machine).delete()` sans DELETE Devis
    préalable lève `ForeignKeyViolation: devis_machine_id_fkey` en Postgres.
    Sur SQLite (test local), les FK sont désactivées par défaut donc le bug
    était masqué — ce test reproduit la situation et garantit que l'ordre
    DELETE est cohérent même si SQLite ne sanctionne pas l'erreur.
    """
    # Crée un devis qui référence machine_id=1 (Mark Andy P5 seedé)
    with SessionLocal() as db:
        devis = Devis(
            entreprise_id=1,  # S12 — scope demo
            numero="TEST-NOTE15-9999",
            payload_input={"test": True},
            payload_output={"test": True},
            mode_calcul="manuel",
            ht_total_eur=Decimal("100.00"),
            format_h_mm=Decimal("40.00"),
            format_l_mm=Decimal("60.00"),
            machine_id=1,
        )
        db.add(devis)
        db.commit()
        # Confirme que le devis est bien persisté
        assert db.query(Devis).filter_by(numero="TEST-NOTE15-9999").count() == 1

    # Re-run seed — doit passer sans erreur quel que soit le dialect DB
    counts = run_seed()
    assert counts["machine"] == 3
    assert counts["client"] == 20

    # Le devis test a été wipé par le seed (conséquence assumée Note 15)
    with SessionLocal() as db:
        assert db.query(Devis).filter_by(numero="TEST-NOTE15-9999").first() is None


def test_note_16_create_multiple_outils_increments_ids_correctly():
    """Note 16 : POST /api/outils en série doit incrémenter les ids
    correctement après le seed.

    Sur Postgres (prod) : valide indirectement que `_reset_postgres_sequences()`
    a bien synchronisé `outil_decoupe_id_seq` à MAX(id) après seed.
    Sur SQLite (test local) : valide nativement (ROWID auto-incrément se
    réaligne sur MAX+1).

    En cas de régression Note 16 sur Postgres, ce test produirait 409 sur la
    1ère création (Postgres tenterait id=1 → conflit avec ligne seedée).
    """
    libelles_test = [
        "note16_outil_a",
        "note16_outil_b",
        "note16_outil_c",
    ]
    ids_crees: list[int] = []
    for libelle in libelles_test:
        r = client.post(
            "/api/outils",
            json={
                "libelle": libelle,
                "format_l_mm": 50,
                "format_h_mm": 30,
                "nb_poses_l": 2,
                "nb_poses_h": 1,
                "forme_speciale": False,
            },
        )
        assert r.status_code == 201, f"POST {libelle} failed: {r.text}"
        ids_crees.append(r.json()["id"])

    # Tous les ids strictement croissants
    assert ids_crees == sorted(ids_crees)
    # Pas de collision avec les 4 outils seedés (ids 1-4)
    assert all(id_ > 4 for id_ in ids_crees)


def test_bornes_elargies_cliche_prix_couleur_at_90():
    """Bornes élargies (mini-sprint Lot M3) : cliche_prix_couleur peut
    désormais accepter 90 € (ancien max=60). Garde-fou métier : ne pas
    régresser sur l'élargissement des bornes en cas de hotfix futur sur
    tarif_poste.csv."""
    r = client.put(
        "/api/tarif-poste/cliche_prix_couleur",
        json={"valeur_defaut": "90.00"},
    )
    assert r.status_code == 200
    assert float(r.json()["valeur_defaut"]) == 90.0


def test_bornes_elargies_outil_base_eur_at_700():
    """Bornes élargies : outil_base_eur peut accepter 700 € (ancien max=500)."""
    r = client.put(
        "/api/tarif-poste/outil_base_eur",
        json={"valeur_defaut": "700.00"},
    )
    assert r.status_code == 200
    assert float(r.json()["valeur_defaut"]) == 700.0


def test_bornes_elargies_above_new_max_still_returns_422():
    """Garde-fou inverse : la borne supérieure existe toujours, juste élargie.
    cliche_prix_couleur à 200 € (nouveau max=100) doit toujours retourner 422.
    """
    r = client.put(
        "/api/tarif-poste/cliche_prix_couleur",
        json={"valeur_defaut": "200.00"},
    )
    assert r.status_code == 422
    assert "valeur_max" in r.json()["detail"]
