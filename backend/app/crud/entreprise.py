from sqlalchemy.orm import Session

from app.models import Entreprise
from app.schemas.entreprise import EntrepriseUpdate

ENTREPRISE_ID = 1  # singleton : une seule ligne, id figé


def get_entreprise(db: Session) -> Entreprise | None:
    return db.query(Entreprise).filter(Entreprise.id == ENTREPRISE_ID).first()


def update_entreprise(db: Session, data: EntrepriseUpdate) -> Entreprise | None:
    entreprise = get_entreprise(db)
    if entreprise is None:
        return None

    # exclude_unset=True : seuls les champs explicitement fournis dans le body
    # sont appliqués. Les autres conservent leur valeur actuelle.
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entreprise, field, value)

    db.commit()
    db.refresh(entreprise)
    return entreprise
