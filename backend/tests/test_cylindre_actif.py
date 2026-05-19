"""Tests parc cylindres compte demo + champ actif (Brief #28 commit 1).

Couvre :
  - Le catalogue par défaut comporte bien 21 cylindres actifs.
  - Les cylindres désactivés (actif=False) ne sont pas retournés par
    `charger_cylindres_actifs` (filtre du moteur d'optim).
  - Les cylindres désactivés restent récupérables via DB pour préservation
    FK historiques (devis sauvegardés sur cyls maintenant inactifs).
"""
from sqlalchemy.orm import Session

from app.data.catalogue_defaults import CYLINDRES_STANDARD_DENTS
from app.db import SessionLocal
from app.models import CylindreMagnetique
from app.services.optimisation_loader import charger_cylindres_actifs


def test_seed_compte_demo_21_cylindres_actifs():
    """Le catalogue par défaut compte 21 cyls, plage 80..187 dents."""
    assert len(CYLINDRES_STANDARD_DENTS) == 21
    assert set(CYLINDRES_STANDARD_DENTS) == {
        80, 82, 84, 86, 88, 92, 96, 98, 101, 104, 106,
        112, 116, 120, 128, 132, 134, 136, 144, 148, 187,
    }


def test_cylindres_desactives_pas_dans_optim():
    """`charger_cylindres_actifs` filtre sur actif=True et ignore les
    cyls désactivés (suppression douce). On crée 2 cyls fictifs (un actif,
    un inactif) et on vérifie que seul l'actif est retourné."""
    with SessionLocal() as db:
        cyl_actif = CylindreMagnetique(
            entreprise_id=1, developpe_mm=999.0, actif=True
        )
        cyl_inactif = CylindreMagnetique(
            entreprise_id=1, developpe_mm=998.0, actif=False
        )
        db.add_all([cyl_actif, cyl_inactif])
        db.commit()
        actifs = charger_cylindres_actifs(db, entreprise_id=1)
        ids_actifs = {c.id for c in actifs}
        assert cyl_actif.id in ids_actifs
        assert cyl_inactif.id not in ids_actifs


def test_cylindres_desactives_conserves_pour_fk():
    """Un cyl désactivé reste lisible via une requête directe sur la DB
    (préservation FK des devis historiques). C'est seulement le moteur
    d'optim qui les ignore."""
    with SessionLocal() as db:
        cyl_inactif = CylindreMagnetique(
            entreprise_id=1, developpe_mm=997.0, actif=False
        )
        db.add(cyl_inactif)
        db.commit()
        cyl_id = cyl_inactif.id
        # Lecture directe : le row existe, juste actif=False.
        reloaded: Session = db.get(CylindreMagnetique, cyl_id)
        assert reloaded is not None
        assert reloaded.actif is False
        assert float(reloaded.developpe_mm) == 997.0
