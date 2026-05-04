from app.crud.outil_decoupe import (
    get_outil_decoupe,
    list_outils_decoupe_actifs,
)
from app.db import SessionLocal
from app.models import OutilDecoupe


def test_seed_loads_4_outils():
    with SessionLocal() as db:
        outils = list_outils_decoupe_actifs(db)
    assert len(outils) == 4
    libelles = {o.libelle for o in outils}
    assert libelles == {
        "outil_60x40_3p1d",
        "outil_80x50_2p1d",
        "outil_30x20_6p2d",
        "outil_100x70_2p1d_forme",
    }


def test_get_outil_decoupe_existing():
    """Outil id=1 = outil_60x40_3p1d, format 60×40, 3 poses largeur."""
    with SessionLocal() as db:
        outil = get_outil_decoupe(db, 1)
    assert outil is not None
    assert outil.libelle == "outil_60x40_3p1d"
    assert outil.format_l_mm == 60
    assert outil.format_h_mm == 40
    assert outil.nb_poses_l == 3
    assert outil.nb_poses_h == 1
    assert outil.forme_speciale is False
    assert outil.actif is True


def test_get_outil_decoupe_missing_returns_none():
    with SessionLocal() as db:
        assert get_outil_decoupe(db, 9999) is None


def test_list_outils_decoupe_actifs_excludes_inactive():
    """Crée un outil inactif et vérifie qu'il n'apparaît pas dans list_actifs."""
    with SessionLocal() as db:
        db.add(
            OutilDecoupe(
                entreprise_id=1,  # S12 — scope demo
                libelle="outil_test_inactif",
                format_l_mm=50,
                format_h_mm=30,
                nb_poses_l=4,
                nb_poses_h=1,
                forme_speciale=False,
                actif=False,
            )
        )
        db.commit()
        actifs = list_outils_decoupe_actifs(db)
    # 4 seedés actifs uniquement, pas l'outil inactif ajouté
    assert len(actifs) == 4
    assert all(o.actif for o in actifs)
    assert "outil_test_inactif" not in {o.libelle for o in actifs}


def test_seeded_outil_forme_speciale_flag():
    """outil_100x70_2p1d_forme (id=4) doit avoir forme_speciale=True."""
    with SessionLocal() as db:
        outil = get_outil_decoupe(db, 4)
    assert outil is not None
    assert outil.forme_speciale is True
    assert outil.format_l_mm == 100
    assert outil.format_h_mm == 70
