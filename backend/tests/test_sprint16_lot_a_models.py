"""Tests modèles Sprint 16 Lot A — Module Rebobinage.

Couvre :
  - `MachineRebobineuse` : création, defaults, CASCADE delete
  - `ParametreMandrin` : création, UNIQUE entreprise_id (singleton),
    defaults, CASCADE delete

L'extension `client` (9 colonnes profil rebobinage) est reportée à un
commit séparé (cf. note dans la migration `q1f3a5d7e9c2`). Ses tests
viendront alors.

Ces tests ciblent la couche modèle/ORM (pas d'endpoint).
"""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Entreprise,
    MODES_PAR_DEFAUT,
    MachineRebobineuse,
    ParametreMandrin,
)


# ---------------------------------------------------------------------------
# MachineRebobineuse
# ---------------------------------------------------------------------------


def test_creation_machine_rebobineuse_persistance_champs():
    with SessionLocal() as db:
        mach = MachineRebobineuse(
            entreprise_id=1,
            nom="Test Rebob 1",
            marque="MarqueX",
            modele="ModX-100",
            laize_max_mm=Decimal("220.00"),
            diametre_max_mm=350,
            mandrins_supportes=[25, 38, 76],
            vitesse_pratique_m_min=90,
            cout_horaire_eur=Decimal("48.50"),
            temps_changement_bobine_min=Decimal("1.20"),
            options=["marquage_bobine_inline"],
        )
        db.add(mach)
        db.commit()
        db.refresh(mach)

        assert mach.id is not None
        assert mach.entreprise_id == 1
        assert mach.nom == "Test Rebob 1"
        assert mach.marque == "MarqueX"
        assert float(mach.laize_max_mm) == 220.00
        assert mach.diametre_max_mm == 350
        assert mach.mandrins_supportes == [25, 38, 76]
        assert mach.vitesse_pratique_m_min == 90
        assert float(mach.cout_horaire_eur) == 48.50
        assert float(mach.temps_changement_bobine_min) == 1.20
        assert mach.options == ["marquage_bobine_inline"]
        assert mach.actif is True  # default
        assert mach.date_creation is not None


def test_machine_rebobineuse_cascade_delete_entreprise():
    """Supprimer une entreprise efface en cascade ses rebobineuses."""
    with SessionLocal() as db:
        ent = Entreprise(
            raison_sociale="Entreprise rebob test",
            siret="00000000001234",
        )
        db.add(ent)
        db.flush()
        mach = MachineRebobineuse(
            entreprise_id=ent.id,
            nom="Mach cascade",
            laize_max_mm=Decimal("200"),
            diametre_max_mm=400,
            vitesse_pratique_m_min=80,
            cout_horaire_eur=Decimal("40"),
            temps_changement_bobine_min=Decimal("1.5"),
        )
        db.add(mach)
        db.commit()
        mach_id = mach.id
        ent_id = ent.id

        db.delete(ent)
        db.commit()

        assert (
            db.query(MachineRebobineuse).filter_by(id=mach_id).first() is None
        )
        assert db.query(Entreprise).filter_by(id=ent_id).first() is None


# Note : les tests « seed demo présent » sur entreprise_id=1 sont
# couverts au niveau migration (cycle up/down/up validé localement +
# `INSERT WHERE NOT EXISTS` idempotent). Ils ne sont pas reproductibles
# au niveau pytest car le `seed_db_before_each_test` du conftest fait
# `DELETE FROM entreprise` qui cascade-purge ces tables avant chaque
# test. La présence en prod est garantie par la migration `q1f3a5d7e9c2`
# qui s'exécute au boot Railway.


# ---------------------------------------------------------------------------
# ParametreMandrin
# ---------------------------------------------------------------------------


def test_modes_par_defaut_constants():
    """Les 3 modes du brief sont exposés via la constante."""
    assert MODES_PAR_DEFAUT == frozenset(
        {"auto", "pre_coupe", "decoupe_interne"}
    )


def test_creation_parametre_mandrin_persistance_champs():
    with SessionLocal() as db:
        # Crée une entreprise dédiée pour éviter conflit UNIQUE avec demo (id=1)
        ent = Entreprise(
            raison_sociale="Entreprise pm test",
            siret="00000000005678",
        )
        db.add(ent)
        db.flush()

        pm = ParametreMandrin(
            entreprise_id=ent.id,
            scie_disponible=True,
            delai_livraison_fournisseur_jours=7,
            stock_securite_par_modele={"25": 100, "76": 50},
            mode_par_defaut="pre_coupe",
        )
        db.add(pm)
        db.commit()
        db.refresh(pm)

        assert pm.id is not None
        assert pm.entreprise_id == ent.id
        assert pm.scie_disponible is True
        assert pm.delai_livraison_fournisseur_jours == 7
        assert pm.stock_securite_par_modele == {"25": 100, "76": 50}
        assert pm.mode_par_defaut == "pre_coupe"
        assert pm.date_creation is not None
        assert pm.date_maj is not None


def test_parametre_mandrin_unique_entreprise_id_singleton():
    """Une 2e row pour la même entreprise → IntegrityError (UNIQUE)."""
    with SessionLocal() as db:
        ent = Entreprise(
            raison_sociale="Entreprise unique test",
            siret="00000000009999",
        )
        db.add(ent)
        db.flush()

        db.add(
            ParametreMandrin(
                entreprise_id=ent.id, scie_disponible=True, mode_par_defaut="auto"
            )
        )
        db.commit()

        db.add(
            ParametreMandrin(
                entreprise_id=ent.id, scie_disponible=False, mode_par_defaut="pre_coupe"
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_parametre_mandrin_defaults_via_orm():
    with SessionLocal() as db:
        ent = Entreprise(
            raison_sociale="Entreprise default test",
            siret="00000000001111",
        )
        db.add(ent)
        db.flush()

        pm = ParametreMandrin(entreprise_id=ent.id)
        db.add(pm)
        db.commit()
        db.refresh(pm)

        # default Python : scie_disponible=False, mode_par_defaut="auto"
        assert pm.scie_disponible is False
        assert pm.mode_par_defaut == "auto"
        assert pm.delai_livraison_fournisseur_jours is None
        assert pm.stock_securite_par_modele is None


def test_parametre_mandrin_cascade_delete_entreprise():
    with SessionLocal() as db:
        ent = Entreprise(
            raison_sociale="Entreprise pm cascade",
            siret="00000000002222",
        )
        db.add(ent)
        db.flush()
        pm = ParametreMandrin(entreprise_id=ent.id, scie_disponible=True)
        db.add(pm)
        db.commit()
        pm_id = pm.id
        ent_id = ent.id

        db.delete(ent)
        db.commit()

        assert db.query(ParametreMandrin).filter_by(id=pm_id).first() is None
        assert db.query(Entreprise).filter_by(id=ent_id).first() is None


# Extension `client` (9 colonnes profil rebobinage) reportée à un commit
# séparé. Tests reviendront avec la migration correspondante.
