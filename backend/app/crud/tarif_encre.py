from sqlalchemy.orm import Session

from app.models import TarifEncre
from app.schemas.tarif_encre import TarifEncreCreate, TarifEncreUpdate


def list_tarifs_encre(db: Session, skip: int = 0, limit: int = 50) -> list[TarifEncre]:
    return (
        db.query(TarifEncre)
        .order_by(TarifEncre.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_tarif_encre(db: Session, tarif_id: int) -> TarifEncre | None:
    return db.query(TarifEncre).filter(TarifEncre.id == tarif_id).first()


def get_by_type_encre(db: Session, type_encre: str) -> TarifEncre | None:
    """Accès par clé symbolique (`process_cmj`, `pantone`, ...) pour le moteur v2.

    Utilisé par le calculateur Poste 2 Encres pour résoudre chaque clé
    de `nb_couleurs_par_type` en tarif d'achat. Si retourne None, le
    calculateur lève CostEngineError("type_encre '...' inconnu").
    """
    return db.query(TarifEncre).filter(TarifEncre.type_encre == type_encre).first()


def create_tarif_encre(db: Session, data: TarifEncreCreate) -> TarifEncre:
    # S12-A : entreprise_id=1 (compte demo). S12-C remplacera par user.entreprise_id
    tarif = TarifEncre(entreprise_id=1, **data.model_dump())
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
