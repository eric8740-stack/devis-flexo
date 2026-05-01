from sqlalchemy.orm import Session

from app.models import Machine
from app.schemas.machine import MachineCreate, MachineUpdate


def list_machines(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    include_inactives: bool = False,
) -> list[Machine]:
    """Sprint 9 v2 — `include_inactives=False` (default) filtre actif=True.

    Cohérent avec le pattern catalogues : les sélections frontend
    `/devis/nouveau` consomment la liste filtrée, l'UI `/parametres/machines`
    passe `include_inactives=true` pour voir aussi les inactives.
    """
    query = db.query(Machine)
    if not include_inactives:
        query = query.filter(Machine.actif.is_(True))
    return query.order_by(Machine.id).offset(skip).limit(limit).all()


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
    """Sprint 9 v2 — soft delete (passe `actif=False`).

    Préserve l'intégrité historique : les devis sauvegardés référencent
    `machine_id` dans leur snapshot, la machine reste consultable
    individuellement après désactivation.
    """
    machine = get_machine(db, machine_id)
    if machine is None:
        return False
    machine.actif = False
    db.commit()
    return True


def reactiver_machine(db: Session, machine_id: int) -> bool:
    """Sprint 9 v2 — passe `actif=True` pour réintroduire une machine archivée."""
    machine = get_machine(db, machine_id)
    if machine is None:
        return False
    machine.actif = True
    db.commit()
    return True
