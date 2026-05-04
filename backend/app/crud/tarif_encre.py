from sqlalchemy.orm import Session

from app.models import TarifEncre
from app.schemas.tarif_encre import TarifEncreCreate, TarifEncreUpdate


def list_tarifs_encre(
    db: Session, entreprise_id: int, skip: int = 0, limit: int = 50
) -> list[TarifEncre]:
    """Sprint 12-C : filtré par entreprise_id."""
    return (
        db.query(TarifEncre)
        .filter(TarifEncre.entreprise_id == entreprise_id)
        .order_by(TarifEncre.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_tarif_encre(db: Session, tarif_id: int) -> TarifEncre | None:
    """Lookup par id (sans scope — usage interne uniquement)."""
    return db.query(TarifEncre).filter(TarifEncre.id == tarif_id).first()


def get_by_type_encre(
    db: Session, type_encre: str, entreprise_id: int
) -> TarifEncre | None:
    """Accès par clé symbolique scopé par entreprise.

    Utilisé par le calculateur Poste 2 Encres via `MoteurDevis(db, entreprise_id)`.
    Sprint 12-C : `entreprise_id` désormais requis pour le scope.
    """
    return (
        db.query(TarifEncre)
        .filter(
            TarifEncre.type_encre == type_encre,
            TarifEncre.entreprise_id == entreprise_id,
        )
        .first()
    )


def create_tarif_encre(
    db: Session, data: TarifEncreCreate, entreprise_id: int
) -> TarifEncre:
    """S12-C : `entreprise_id` injecté par le router via user.entreprise_id."""
    tarif = TarifEncre(entreprise_id=entreprise_id, **data.model_dump())
    db.add(tarif)
    db.commit()
    db.refresh(tarif)
    return tarif


def update_tarif_encre(
    db: Session, tarif_id: int, data: TarifEncreUpdate
) -> TarifEncre | None:
    tarif = get_tarif_encre(db, tarif_id)
    if tarif is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tarif, field, value)
    db.commit()
    db.refresh(tarif)
    return tarif
