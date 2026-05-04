from sqlalchemy.orm import Session

from app.models import Fournisseur
from app.schemas.fournisseur import FournisseurCreate, FournisseurUpdate


def list_fournisseurs(
    db: Session, skip: int = 0, limit: int = 50
) -> list[Fournisseur]:
    return (
        db.query(Fournisseur)
        .order_by(Fournisseur.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_fournisseur(db: Session, fournisseur_id: int) -> Fournisseur | None:
    return (
        db.query(Fournisseur).filter(Fournisseur.id == fournisseur_id).first()
    )


def create_fournisseur(db: Session, data: FournisseurCreate) -> Fournisseur:
    # S12-A : entreprise_id=1 (compte demo). S12-C remplacera par user.entreprise_id
    fournisseur = Fournisseur(entreprise_id=1, **data.model_dump())
    db.add(fournisseur)
    db.commit()
    db.refresh(fournisseur)
    return fournisseur


def update_fournisseur(
    db: Session, fournisseur_id: int, data: FournisseurUpdate
) -> Fournisseur | None:
    fournisseur = get_fournisseur(db, fournisseur_id)
    if fournisseur is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(fournisseur, field, value)
    db.commit()
    db.refresh(fournisseur)
    return fournisseur


def delete_fournisseur(db: Session, fournisseur_id: int) -> bool:
    fournisseur = get_fournisseur(db, fournisseur_id)
    if fournisseur is None:
        return False
    db.delete(fournisseur)
    db.commit()
    return True
