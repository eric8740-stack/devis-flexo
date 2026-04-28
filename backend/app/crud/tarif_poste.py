from sqlalchemy.orm import Session

from app.models import TarifPoste
from app.schemas.tarif_poste import TarifPosteCreate, TarifPosteUpdate


def list_tarifs_poste(db: Session, skip: int = 0, limit: int = 50) -> list[TarifPoste]:
    return (
        db.query(TarifPoste)
        .order_by(TarifPoste.poste_numero, TarifPoste.cle)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_tarif_poste(db: Session, tarif_id: int) -> TarifPoste | None:
    return db.query(TarifPoste).filter(TarifPoste.id == tarif_id).first()


def get_by_cle(db: Session, cle: str) -> TarifPoste | None:
    """Accès par clé symbolique (`matiere_prix_kg_defaut`, ...) pour le moteur v2.

    Le moteur de calcul (Lot 3d) appelle uniquement par cle, jamais par id ni
    libellé — un changement de texte ne casse pas la logique.
    """
    return db.query(TarifPoste).filter(TarifPoste.cle == cle).first()


def create_tarif_poste(db: Session, data: TarifPosteCreate) -> TarifPoste:
    tarif = TarifPoste(**data.model_dump())
    db.add(tarif)
    db.commit()
    db.refresh(tarif)
    return tarif


def update_tarif_poste(
    db: Session, tarif_id: int, data: TarifPosteUpdate
) -> TarifPoste | None:
    tarif = get_tarif_poste(db, tarif_id)
    if tarif is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tarif, field, value)
    db.commit()
    db.refresh(tarif)
    return tarif
