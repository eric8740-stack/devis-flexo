"""Router /api/matieres — catalogue matières scopé tenant.

Sert le sélecteur du formulaire /optimisation (auto-fill épaisseur +
transparence) et la page Paramètres > Matières quand elle existera.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Matiere, User
from app.schemas.matiere import MatiereOut


router = APIRouter(prefix="/api/matieres", tags=["matieres"])


@router.get("", response_model=list[MatiereOut])
def list_matieres(
    actif: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MatiereOut]:
    """Liste les matières du tenant, triées par libellé.

    Filtrage par défaut sur `actif=True`. Passer `?actif=false` pour
    inclure les matières désactivées (page admin).
    """
    query = db.query(Matiere).filter(Matiere.entreprise_id == user.entreprise_id)
    if actif:
        query = query.filter(Matiere.actif.is_(True))
    return [MatiereOut.model_validate(m) for m in query.order_by(Matiere.libelle).all()]
