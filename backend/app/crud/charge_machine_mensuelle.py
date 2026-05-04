from sqlalchemy.orm import Session

from app.models import ChargeMachineMensuelle
from app.schemas.charge_machine_mensuelle import (
    ChargeMachineMensuelleCreate,
    ChargeMachineMensuelleUpdate,
)


def list_charges_machine(
    db: Session, skip: int = 0, limit: int = 50
) -> list[ChargeMachineMensuelle]:
    return (
        db.query(ChargeMachineMensuelle)
        .order_by(
            ChargeMachineMensuelle.annee.desc(), ChargeMachineMensuelle.mois.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_charge_machine(
    db: Session, charge_id: int
) -> ChargeMachineMensuelle | None:
    return (
        db.query(ChargeMachineMensuelle)
        .filter(ChargeMachineMensuelle.id == charge_id)
        .first()
    )


def create_charge_machine(
    db: Session, data: ChargeMachineMensuelleCreate, entreprise_id: int
) -> ChargeMachineMensuelle:
    """S12-C : `entreprise_id` injecté par le router via user.entreprise_id.
    cout_horaire_calcule absent volontairement : hook before_insert le calcule."""
    charge = ChargeMachineMensuelle(
        entreprise_id=entreprise_id, **data.model_dump()
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def update_charge_machine(
    db: Session, charge_id: int, data: ChargeMachineMensuelleUpdate
) -> ChargeMachineMensuelle | None:
    charge = get_charge_machine(db, charge_id)
    if charge is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(charge, field, value)
    # cout_horaire_calcule recalculé par hook before_update.
    db.commit()
    db.refresh(charge)
    return charge
