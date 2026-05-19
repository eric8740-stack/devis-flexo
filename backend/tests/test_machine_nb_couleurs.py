"""Tests Machine.nb_groupes_couleurs (Brief #30 commit 2)."""
from app.db import SessionLocal
from app.models import MachineImprimerie


def test_champ_nb_groupes_couleurs_existe_sur_machine_imprimerie():
    """Le champ `nb_groupes_couleurs` existe sur MachineImprimerie
    (sémantique brief #30 'nb couleurs imprimables = PC montés')."""
    with SessionLocal() as db:
        m = db.query(MachineImprimerie).first()
    if m is None:
        # Cas test isolé sans seed : on vérifie juste le mapping ORM.
        from sqlalchemy import inspect

        insp = inspect(MachineImprimerie)
        cols = {c.key for c in insp.columns}
        assert "nb_groupes_couleurs" in cols
        return
    assert hasattr(m, "nb_groupes_couleurs")


def test_seed_compte_demo_machines_nb_groupes_couleurs_renseigne():
    """La migration g8a4f9c2e5b1 garantit nb_groupes_couleurs renseigné
    pour les machines compte demo (Mark Andy 2200=8, OMET XFlex 330=10,
    Nilpeter FA-22=8)."""
    with SessionLocal() as db:
        machines = (
            db.query(MachineImprimerie)
            .filter_by(entreprise_id=1)
            .all()
        )
    cible = {
        "Mark Andy 2200": 8,
        "OMET XFlex 330": 10,
        "Nilpeter FA-22": 8,
    }
    for m in machines:
        if m.nom in cible:
            assert m.nb_groupes_couleurs == cible[m.nom], (
                f"{m.nom} attendu {cible[m.nom]}, obtenu {m.nb_groupes_couleurs}"
            )
