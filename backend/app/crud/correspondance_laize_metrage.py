from sqlalchemy.orm import Session

from app.models import CorrespondanceLaizeMetrage
from app.schemas.correspondance_laize_metrage import (
    CorrespondanceLaizeMetrageCreate,
    CorrespondanceLaizeMetrageUpdate,
)


def list_correspondances(
    db: Session, skip: int = 0, limit: int = 100
) -> list[CorrespondanceLaizeMetrage]:
    return (
        db.query(CorrespondanceLaizeMetrage)
        .order_by(CorrespondanceLaizeMetrage.laize_mm)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_correspondance(
    db: Session, corr_id: int
) -> CorrespondanceLaizeMetrage | None:
    return (
        db.query(CorrespondanceLaizeMetrage)
        .filter(CorrespondanceLaizeMetrage.id == corr_id)
        .first()
    )


def create_correspondance(
    db: Session, data: CorrespondanceLaizeMetrageCreate
) -> CorrespondanceLaizeMetrage:
    corr = CorrespondanceLaizeMetrage(**data.model_dump())
    db.add(corr)
    db.commit()
    db.refresh(corr)
    return corr


def update_correspondance(
    db: Session, corr_id: int, data: CorrespondanceLaizeMetrageUpdate
) -> CorrespondanceLaizeMetrage | None:
    corr = get_correspondance(db, corr_id)
    if corr is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(corr, field, value)
    db.commit()
    db.refresh(corr)
    return corr
