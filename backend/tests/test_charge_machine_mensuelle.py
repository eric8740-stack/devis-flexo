from decimal import Decimal

import pytest

from app.crud.charge_machine_mensuelle import (
    create_charge_machine,
    list_charges_machine,
    update_charge_machine,
)
from app.db import SessionLocal
from app.schemas.charge_machine_mensuelle import (
    ChargeMachineMensuelleCreate,
    ChargeMachineMensuelleUpdate,
)


def test_seed_loads_1_charge_with_hook_computed_cout_horaire():
    """Le seed pose 60000 € / 160 h → hook calcule 375.0000 €/h."""
    with SessionLocal() as db:
        charges = list_charges_machine(db)
    assert len(charges) == 1
    assert charges[0].cout_horaire_calcule == Decimal("375.0000")


def test_create_triggers_before_insert_hook():
    """12 000 € / 100 h = 120.0000 €/h, calculé par before_insert."""
    payload = ChargeMachineMensuelleCreate(
        mois=5,
        annee=2026,
        montant_total=Decimal("12000.00"),
        heures_disponibles=Decimal("100.00"),
        source="test create",
    )
    with SessionLocal() as db:
        created = create_charge_machine(db, payload, entreprise_id=1)
    assert created.cout_horaire_calcule == Decimal("120.0000")


def test_update_triggers_before_update_hook():
    """Modifier heures_disponibles recalcule cout_horaire_calcule."""
    with SessionLocal() as db:
        charges = list_charges_machine(db)
        # Seed : 60000 / 160 = 375. Update à 200 h → 60000 / 200 = 300.
        updated = update_charge_machine(
            db,
            charges[0].id,
            ChargeMachineMensuelleUpdate(heures_disponibles=Decimal("200.00")),
        )
    assert updated.cout_horaire_calcule == Decimal("300.0000")


def test_create_with_zero_hours_raises_value_error():
    """Garde-fou division par zéro dans le hook applicatif."""
    payload = ChargeMachineMensuelleCreate.model_construct(
        mois=6,
        annee=2026,
        montant_total=Decimal("5000.00"),
        heures_disponibles=Decimal("0.00"),
        source="test zero",
    )
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="heures_disponibles"):
            create_charge_machine(db, payload, entreprise_id=1)
