from sqlalchemy.orm import Session

from app.models import Client
from app.schemas.client import ClientCreate, ClientUpdate


def list_clients(db: Session, skip: int = 0, limit: int = 50) -> list[Client]:
    return (
        db.query(Client)
        .order_by(Client.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_client(db: Session, client_id: int) -> Client | None:
    return db.query(Client).filter(Client.id == client_id).first()


def create_client(
    db: Session, data: ClientCreate, entreprise_id: int
) -> Client:
    """S12-C : `entreprise_id` injecté par le router via user.entreprise_id."""
    client = Client(entreprise_id=entreprise_id, **data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def update_client(
    db: Session, client_id: int, data: ClientUpdate
) -> Client | None:
    client = get_client(db, client_id)
    if client is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


def delete_client(db: Session, client_id: int) -> bool:
    """Renvoie True si supprimé, False si introuvable."""
    client = get_client(db, client_id)
    if client is None:
        return False
    db.delete(client)
    db.commit()
    return True
