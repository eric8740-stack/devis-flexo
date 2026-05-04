"""Tests modèle Devis (Sprint 4 Lot 4a) — création, contraintes, FK."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Client, Devis, Machine


def _payload_input_v1a() -> dict:
    """Snapshot V1a manuel."""
    return {
        "complexe_id": 31,
        "laize_utile_mm": 220,
        "ml_total": 3000,
        "nb_couleurs_par_type": {"process_cmj": 4, "pantone": 1},
        "machine_id": 1,
        "mode_calcul": "manuel",
        "intervalle_mm": "3",
        "forfaits_st": [{"partenaire_st_id": 1, "montant_eur": "50.00"}],
    }


def _payload_output_v1a() -> dict:
    """Snapshot DevisOutput V1a (HT 1449.09 €, exhaustif simplifié)."""
    return {
        "mode": "manuel",
        "cout_revient_eur": "1228.04",
        "pct_marge_appliquee": "0.18",
        "prix_vente_ht_eur": "1449.09",
        "prix_au_mille_eur": "6.92",
        "postes": [
            {"poste_numero": i, "libelle": f"P{i}", "montant_eur": "100.00", "details": {}}
            for i in range(1, 8)
        ],
    }


def _make_devis(**overrides) -> Devis:
    base = dict(
        # Sprint 12 multi-tenant — entreprise_id=1 (compte demo Eric)
        entreprise_id=1,
        numero="DEV-2026-0001",
        statut="brouillon",
        client_id=None,
        payload_input=_payload_input_v1a(),
        payload_output=_payload_output_v1a(),
        mode_calcul="manuel",
        cylindre_choisi_z=None,
        cylindre_choisi_nb_etiq=None,
        ht_total_eur=Decimal("1449.09"),
        format_h_mm=Decimal("40"),
        format_l_mm=Decimal("60"),
        machine_id=1,
    )
    base.update(overrides)
    return Devis(**base)


def test_devis_create_minimal_v1a_manuel():
    """Création basique d'un devis V1a manuel persisté."""
    with SessionLocal() as db:
        devis = _make_devis()
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            assert devis.id is not None
            assert devis.numero == "DEV-2026-0001"
            assert devis.statut == "brouillon"  # default
            assert devis.mode_calcul == "manuel"
            assert devis.ht_total_eur == Decimal("1449.09")
            assert devis.cylindre_choisi_z is None
            assert devis.date_creation is not None
            assert devis.date_modification is not None
            # JSON correctement persisté + relu
            assert devis.payload_input["mode_calcul"] == "manuel"
            assert devis.payload_output["prix_vente_ht_eur"] == "1449.09"
        finally:
            db.delete(devis)
            db.commit()


def test_devis_create_matching_with_cylindre_choisi():
    """Mode matching : cylindre_choisi_z + cylindre_choisi_nb_etiq remplis."""
    with SessionLocal() as db:
        devis = _make_devis(
            numero="DEV-2026-0002",
            mode_calcul="matching",
            cylindre_choisi_z=134,
            cylindre_choisi_nb_etiq=10,
        )
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            assert devis.mode_calcul == "matching"
            assert devis.cylindre_choisi_z == 134
            assert devis.cylindre_choisi_nb_etiq == 10
        finally:
            db.delete(devis)
            db.commit()


def test_devis_numero_unique_constraint():
    """Deux devis avec le même numero → IntegrityError."""
    with SessionLocal() as db:
        d1 = _make_devis(numero="DEV-2026-0099")
        db.add(d1)
        db.commit()
        try:
            d2 = _make_devis(numero="DEV-2026-0099")
            db.add(d2)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        finally:
            db.delete(d1)
            db.commit()


def test_devis_statut_valide():
    """Statut 'valide' accepté."""
    with SessionLocal() as db:
        devis = _make_devis(numero="DEV-2026-0100", statut="valide")
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            assert devis.statut == "valide"
        finally:
            db.delete(devis)
            db.commit()


def test_devis_machine_id_required():
    """machine_id NOT NULL → IntegrityError si absent."""
    with SessionLocal() as db:
        devis = _make_devis(numero="DEV-2026-0101", machine_id=None)
        db.add(devis)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_devis_client_fk_configured_with_set_null():
    """FK client_id → client.id avec ondelete='SET NULL' (vérif métadonnées).

    Note : en SQLite (dev), les FK ne sont pas appliquées par défaut donc on
    ne peut pas tester la cascade runtime. La vérification porte sur la
    définition de la contrainte (qui sera bien appliquée en Postgres prod).
    """
    fks = [fk for fk in Devis.__table__.foreign_keys if fk.column.table.name == "client"]
    assert len(fks) == 1
    assert fks[0].ondelete == "SET NULL"


def test_devis_client_id_link_when_set():
    """Le lien client_id → client est lisible via db.get."""
    with SessionLocal() as db:
        client = Client(entreprise_id=1, raison_sociale="ClientTestLink")
        db.add(client)
        db.commit()
        db.refresh(client)

        devis = _make_devis(numero="DEV-2026-0102", client_id=client.id)
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            client_lu = db.get(Client, devis.client_id)
            assert client_lu is not None
            assert client_lu.raison_sociale == "ClientTestLink"
        finally:
            db.delete(devis)
            db.delete(client)
            db.commit()


def test_devis_machine_relationship_lookup():
    """Vérifie qu'on peut joindre la machine via machine_id."""
    with SessionLocal() as db:
        devis = _make_devis(numero="DEV-2026-0103")
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            machine = db.get(Machine, devis.machine_id)
            assert machine is not None
            assert machine.nom == "Mark Andy P5"
        finally:
            db.delete(devis)
            db.commit()
