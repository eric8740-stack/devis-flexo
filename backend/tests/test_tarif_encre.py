from decimal import Decimal

from app.crud.tarif_encre import create_tarif_encre, list_tarifs_encre, update_tarif_encre
from app.db import SessionLocal
from app.models import TarifEncre
from app.schemas.tarif_encre import TarifEncreCreate, TarifEncreUpdate


def test_seed_loads_5_tarifs_encre():
    with SessionLocal() as db:
        tarifs = list_tarifs_encre(db)
    assert len(tarifs) == 5
    types = {t.type_encre for t in tarifs}
    assert types == {
        "process_cmj",
        "process_black_hc",
        "pantone",
        "blanc_high_opaque",
        "metallise",
    }


def test_create_tarif_encre_persists():
    payload = TarifEncreCreate(
        type_encre="test_uv_special",
        libelle="Encre UV spéciale (test)",
        prix_kg_defaut=Decimal("32.50"),
    )
    with SessionLocal() as db:
        created = create_tarif_encre(db, payload)
        assert created.id is not None
        assert created.ratio_g_m2_couleur == Decimal("2.000")  # défaut


def test_update_tarif_encre_modifies_price():
    with SessionLocal() as db:
        pantone = (
            db.query(TarifEncre).filter(TarifEncre.type_encre == "pantone").first()
        )
        updated = update_tarif_encre(
            db, pantone.id, TarifEncreUpdate(prix_kg_defaut=Decimal("23.00"))
        )
    assert updated.prix_kg_defaut == Decimal("23.00")
    assert updated.type_encre == "pantone"
