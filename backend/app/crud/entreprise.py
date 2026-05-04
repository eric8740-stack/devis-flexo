"""CRUD entreprise — Sprint 12-C scoped.

Plus de hard-code `ENTREPRISE_ID = 1` (S12-A debranchage singleton). Le
router passe désormais `entreprise_id=user.entreprise_id` explicitement.
"""
from sqlalchemy.orm import Session

from app.models import Entreprise
from app.schemas.entreprise import EntrepriseUpdate


def get_entreprise_by_id(db: Session, entreprise_id: int) -> Entreprise | None:
    """Récupère une entreprise par son id (= user.entreprise_id côté router)."""
    return (
        db.query(Entreprise).filter(Entreprise.id == entreprise_id).first()
    )


def update_entreprise_by_id(
    db: Session, entreprise_id: int, data: EntrepriseUpdate
) -> Entreprise | None:
    entreprise = get_entreprise_by_id(db, entreprise_id)
    if entreprise is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entreprise, field, value)
    db.commit()
    db.refresh(entreprise)
    return entreprise
