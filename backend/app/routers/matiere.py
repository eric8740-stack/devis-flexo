"""Router /api/matieres — catalogue matières scopé tenant.

Sert le sélecteur du formulaire /optimisation (auto-fill épaisseur +
transparence) et la page Paramètres > Matières quand elle existera.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Matiere, User
from app.schemas.matiere import MatiereEpaisseurPatch, MatiereOut
from app.services.scope_service import get_or_404_scoped


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


@router.patch("/{matiere_id}", response_model=MatiereOut)
def patch_matiere_epaisseur(
    matiere_id: int,
    body: MatiereEpaisseurPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatiereOut:
    """Lot E — renseigne l'épaisseur réelle (`epaisseur_microns`) d'une matière.

    Scope tenant strict via `get_or_404_scoped` (404 anti-énumération si
    cross-tenant). Sert à éliminer le fallback 150 µm du calcul de Ø en
    saisissant la vraie épaisseur sur les matières qui l'avaient à NULL.
    """
    matiere = get_or_404_scoped(db, Matiere, matiere_id, user)
    matiere.epaisseur_microns = body.epaisseur_microns
    db.commit()
    db.refresh(matiere)
    return MatiereOut.model_validate(matiere)
