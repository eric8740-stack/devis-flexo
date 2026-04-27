from sqlalchemy.orm import Session

from app.models import Machine
from app.schemas.machine import MachineCreate, MachineUpdate


def list_machines(db: Session, skip: int = 0, limit: int = 50) -> list[Machine]:
    return (
        db.query(Machine).order_by(Machine.id).offset(skip).limit(limit).all()
    )


def get_machine(db: Session, machine_id: int) -> Machine | None:
    return db.query(Machine).filter(Machine.id == machine_id).first()


def create_machine(db: Session, data: MachineCreate) -> Machine:
    machine = Machine(**data.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


def update_machine(
    db: Session, machine_id: int, data: MachineUpdate
) -> Machine | None:
    machine = get_machine(db, machine_id)
    if machine is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(machine, field, value)
    db.commit()
    db.refresh(machine)
    return machine


def delete_machine(db: Session, machine_id: int) -> bool:
    machine = get_machine(db, machine_id)
    if machine is None:
        return False
    db.delete(machine)
    db.commit()
    return True
