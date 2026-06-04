"""#4.3 — `Machine.type_machine` (presse/finition) + filtrage loader optim.

- Le champ a un défaut "presse" (toute machine est une presse sauf re-typée).
- Le loader d'optim `charger_machines_actives` ne charge QUE les presses : une
  ligne de finition (Daco, Rotoflex) ne génère plus de candidat.
- Le seed démo type bien Daco D250 en "finition" (les presses restent "presse").

SACRED : un filtre de candidats ne touche pas le moteur de coût → V1a / tripwire
inchangés (couverts par leurs propres tests).
"""
from __future__ import annotations

from decimal import Decimal

from app.db import SessionLocal
from app.models import Entreprise, Machine
from app.models.machine import TYPES_MACHINE
from app.services.optimisation_loader import charger_machines_actives


DEMO = 1


def test_types_machine_constante():
    assert TYPES_MACHINE == {"presse", "finition"}


def test_type_machine_defaut_presse_via_orm():
    """Une Machine créée sans type_machine est une 'presse' (server_default)."""
    with SessionLocal() as db:
        ent = db.query(Entreprise).filter_by(id=99).first()
        if ent is None:
            db.add(Entreprise(id=99, raison_sociale="T99", siret=f"{99:014d}"))
            db.commit()
        m = Machine(
            entreprise_id=99,
            nom="TEST 43 defaut",
            laize_max_mm=Decimal("330.00"),
            vitesse_moyenne_m_h=4800,
            actif=True,
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        try:
            assert m.type_machine == "presse"
        finally:
            db.delete(m)
            db.commit()


def test_loader_exclut_finition_garde_presse():
    """Le loader optim renvoie la presse mais PAS la finition (même tenant,
    même vitesse → seule la différence de rôle compte)."""
    with SessionLocal() as db:
        ent = db.query(Entreprise).filter_by(id=99).first()
        if ent is None:
            db.add(Entreprise(id=99, raison_sociale="T99", siret=f"{99:014d}"))
            db.commit()
        presse = Machine(
            entreprise_id=99, nom="TEST 43 presse",
            laize_max_mm=Decimal("330.00"), vitesse_moyenne_m_h=4800,
            actif=True, type_machine="presse",
        )
        finition = Machine(
            entreprise_id=99, nom="TEST 43 finition",
            laize_max_mm=Decimal("330.00"), vitesse_moyenne_m_h=4800,
            actif=True, type_machine="finition",
        )
        db.add_all([presse, finition])
        db.commit()
        try:
            noms = [m.nom for m in charger_machines_actives(db, 99)]
            assert "TEST 43 presse" in noms
            assert "TEST 43 finition" not in noms
        finally:
            db.delete(presse)
            db.delete(finition)
            db.commit()


def test_seed_demo_daco_finition_presses_presse():
    """Le seed démo (autouse) type Daco D250 en 'finition', les presses en
    'presse'. Garantit que le re-seed ne réintroduit pas Daco comme presse."""
    with SessionLocal() as db:
        par_nom = {
            m.nom: m.type_machine
            for m in db.query(Machine).filter_by(entreprise_id=DEMO).all()
        }
    assert par_nom["Daco D250 ligne finition"] == "finition"
    assert par_nom["Mark Andy P5"] == "presse"
    assert par_nom["Atelier 2 (vieille presse)"] == "presse"
