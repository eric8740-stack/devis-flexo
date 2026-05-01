from decimal import Decimal

from app.crud.tarif_poste import (
    create_tarif_poste,
    get_by_cle,
    list_tarifs_poste,
    update_tarif_poste,
)
from app.db import SessionLocal
from app.schemas.tarif_poste import TarifPosteCreate, TarifPosteUpdate


def test_seed_loads_10_tarifs_poste():
    """Sprint 9 v2 : 7 préexistants + 3 nouveaux outillage (Dette 1 migrée)."""
    with SessionLocal() as db:
        assert len(list_tarifs_poste(db)) == 10


def test_get_by_cle_returns_matching_record():
    with SessionLocal() as db:
        tarif = get_by_cle(db, "matiere_prix_kg_defaut")
    assert tarif is not None
    assert tarif.poste_numero == 1
    assert tarif.valeur_defaut == Decimal("1.7500")
    assert tarif.unite == "€/kg"


def test_get_by_cle_returns_none_when_missing():
    with SessionLocal() as db:
        assert get_by_cle(db, "cle_inexistante_xyz") is None


def test_create_tarif_poste_persists():
    payload = TarifPosteCreate(
        cle="test_param_unique",
        poste_numero=2,
        libelle="Paramètre test",
        valeur_defaut=Decimal("12.3400"),
        unite="€",
    )
    with SessionLocal() as db:
        created = create_tarif_poste(db, payload)
        assert created.id is not None
        assert created.actif is True
        # vérifie qu'il est retrouvable par cle
        assert get_by_cle(db, "test_param_unique").id == created.id


def test_update_tarif_poste_modifies_field():
    # Le seed contient cliche_prix_couleur (id=2, valeur 45)
    with SessionLocal() as db:
        original = get_by_cle(db, "cliche_prix_couleur")
        updated = update_tarif_poste(
            db, original.id, TarifPosteUpdate(valeur_defaut=Decimal("50.0000"))
        )
    assert updated.valeur_defaut == Decimal("50.0000")
    assert updated.cle == "cliche_prix_couleur"  # non touché
