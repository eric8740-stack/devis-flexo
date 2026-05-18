"""Tests modèle LotProduction (Sprint 13 avenant — PR A commit 2).

Couvre :
  - Création basique d'un lot rattaché à un devis.
  - Cascade delete : supprimer un devis supprime ses lots.
  - UniqueConstraint(devis_id, ordre) : pas de deux lots avec même ordre.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import (
    Bareme,
    CylindreMagnetique,
    Devis,
    LotProduction,
    MachineImprimerie,
    Matiere,
    OptionFabrication,
)

_http = TestClient(app)


def _onboard_if_needed():
    """Onboarde le tenant 1 si nécessaire pour avoir cyl/mach/mat seedés.

    Idempotent : si déjà onboardé, l'endpoint renvoie 409 et on l'ignore.
    """
    db: Session = SessionLocal()
    try:
        existant = db.query(CylindreMagnetique).filter_by(entreprise_id=1).first()
        if existant:
            return
        # Sinon purge éventuels résidus et onboard via API.
        for ent_id in (1,):
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
    finally:
        db.close()
    r = _http.post(
        "/api/onboarding/initialiser-catalogues",
        json={
            "cylindres_developpes_mm": [304.8, 330.2],
            "machines_codes": ["mark_andy_2200"],
            "matieres_codes": [],
            "options_codes": [],
        },
    )
    assert r.status_code == 201, r.text
    # Onboarding ne crée pas de matière par défaut, on en ajoute une simple
    # directement pour valider le FK lot_production.matiere_id.
    db: Session = SessionLocal()
    try:
        if db.query(Matiere).filter_by(entreprise_id=1).first() is None:
            db.add(
                Matiere(
                    entreprise_id=1,
                    code="test_pp",
                    libelle="Test PP couché",
                    actif=True,
                )
            )
            db.commit()
    finally:
        db.close()


def _create_devis_minimal(db: Session, numero: str = "TEST-LOT-001") -> Devis:
    """Crée un Devis minimal pour servir de parent aux lots.

    On utilise des champs JSON vides + IDs seedés (machine_id=1 si seedé).
    Le but est uniquement de tester la table LotProduction.
    """
    devis = Devis(
        entreprise_id=1,
        numero=numero,
        payload_input={"machine_id": 1},
        payload_output={"prix_vente_ht_eur": "0"},
        mode_calcul="manuel",
        ht_total_eur=0,
        format_h_mm=40,
        format_l_mm=60,
        machine_id=1,
    )
    db.add(devis)
    db.flush()
    return devis


def _get_fk_ids(db: Session) -> tuple[int, int, int]:
    """Retourne (cylindre_id, machine_imprimerie_id, matiere_id) seedés
    pour l'entreprise 1. Assume que `_onboard_if_needed()` a été appelé."""
    cyl = db.query(CylindreMagnetique).filter_by(entreprise_id=1).first()
    mach = db.query(MachineImprimerie).filter_by(entreprise_id=1).first()
    mat = db.query(Matiere).filter_by(entreprise_id=1).first()
    assert cyl and mach and mat, "_onboard_if_needed() doit être appelé avant"
    return cyl.id, mach.id, mat.id


def test_creation_lot_production():
    """Crée un LotProduction et vérifie la persistance des champs clés."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)
        devis = _create_devis_minimal(db)
        lot = LotProduction(
            devis_id=devis.id,
            entreprise_id=1,
            ordre=1,
            cylindre_id=cyl_id,
            machine_id=mach_id,
            nb_poses_dev=2,
            nb_poses_laize=3,
            sens_enroulement=1,
            quantite=5000,
            matiere_id=mat_id,
        )
        db.add(lot)
        db.commit()
        db.refresh(lot)
        assert lot.id is not None
        assert lot.devis_id == devis.id
        assert lot.entreprise_id == 1
        assert lot.ordre == 1
        assert lot.nb_poses_dev == 2
        assert lot.nb_poses_laize == 3
        assert lot.sens_enroulement == 1
        assert lot.quantite == 5000
        assert lot.matiere_id == mat_id


def test_cascade_delete_devis_supprime_lots():
    """Supprimer un devis efface en cascade ses lots (cascade=delete-orphan)."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)
        devis = _create_devis_minimal(db, numero="TEST-LOT-CASCADE-001")
        lot = LotProduction(
            devis_id=devis.id,
            entreprise_id=1,
            ordre=1,
            cylindre_id=cyl_id,
            machine_id=mach_id,
            nb_poses_dev=2,
            nb_poses_laize=3,
            sens_enroulement=1,
            quantite=1000,
            matiere_id=mat_id,
        )
        db.add(lot)
        db.commit()
        lot_id = lot.id
        devis_id = devis.id

        # Supprime le devis → le lot doit disparaître via cascade
        db.delete(devis)
        db.commit()

        assert db.query(LotProduction).filter_by(id=lot_id).first() is None
        assert db.query(Devis).filter_by(id=devis_id).first() is None


def test_unique_constraint_devis_ordre():
    """Deux lots avec mêmes (devis_id, ordre) → IntegrityError."""
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)
        devis = _create_devis_minimal(db, numero="TEST-LOT-UNIQ-001")
        lot1 = LotProduction(
            devis_id=devis.id,
            entreprise_id=1,
            ordre=1,
            cylindre_id=cyl_id,
            machine_id=mach_id,
            nb_poses_dev=1,
            nb_poses_laize=1,
            sens_enroulement=1,
            quantite=100,
            matiere_id=mat_id,
        )
        db.add(lot1)
        db.commit()

        lot2_meme_ordre = LotProduction(
            devis_id=devis.id,
            entreprise_id=1,
            ordre=1,  # même ordre que lot1
            cylindre_id=cyl_id,
            machine_id=mach_id,
            nb_poses_dev=1,
            nb_poses_laize=1,
            sens_enroulement=2,
            quantite=200,
            matiere_id=mat_id,
        )
        db.add(lot2_meme_ordre)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
