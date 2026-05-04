"""Endpoints HTTP des paramètres tarifaires — Sprint 12-C scoped.

`tarif_poste` est désormais scopé par entreprise : chaque imprimeur
a ses 10 paramètres tarifaires (cliche_prix_couleur, calage_forfait,
outil_base_eur, etc.). Le compte demo Eric (entreprise_id=1) a les
10 lignes seedées ; les nouvelles entreprises créées via /register
n'ont pas encore de tarifs (TODO S12-D : seed des tarifs par défaut
à l'inscription pour donner aux nouveaux comptes une base éditable).

Routes :
  GET    /api/tarif-poste                 → liste groupée par poste_numero
  GET    /api/tarif-poste/{cle}           → détail d'une clé
  PUT    /api/tarif-poste/{cle}           → modifier valeur_defaut (validation min/max)
  POST   /api/tarif-poste/reset/{poste}   → reset aux valeurs initiales (seed CSV)
"""
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.crud import tarif_poste as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.tarif_poste import (
    LIBELLE_POSTE,
    ResetPosteResponse,
    TarifPosteByPoste,
    TarifPosteRead,
    TarifPosteUpdateValeur,
    TarifsGrouped,
)

router = APIRouter(prefix="/api/tarif-poste", tags=["tarif-poste"])


@router.get("", response_model=TarifsGrouped)
def list_tarifs_grouped(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Renvoie les paramètres tarifaires de l'entreprise du user, groupés
    par poste_numero. Tri intra-poste sur `ordre_affichage`."""
    tarifs = crud.list_tarifs_poste(db, user.entreprise_id, limit=200)
    grouped: dict[int, list[TarifPosteRead]] = {}
    for t in tarifs:
        grouped.setdefault(t.poste_numero, []).append(TarifPosteRead.model_validate(t))
    postes = [
        TarifPosteByPoste(
            poste_numero=numero,
            libelle_poste=LIBELLE_POSTE.get(numero, f"Poste {numero}"),
            parametres=parametres,
        )
        for numero, parametres in sorted(grouped.items())
    ]
    return TarifsGrouped(postes=postes)


@router.get("/{cle}", response_model=TarifPosteRead)
def get_tarif_by_cle(
    cle: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tarif = crud.get_by_cle(db, cle, user.entreprise_id)
    if tarif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paramètre tarifaire {cle!r} introuvable",
        )
    return tarif


@router.put("/{cle}", response_model=TarifPosteRead)
def update_tarif_valeur(
    cle: str,
    data: TarifPosteUpdateValeur,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Modifie la valeur courante d'un paramètre de l'entreprise du user.

    Lève 404 si la clé n'existe pas, 422 si la valeur sort des bornes.
    """
    try:
        tarif = crud.update_valeur_by_cle(
            db, cle, data.valeur_defaut, user.entreprise_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    if tarif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paramètre tarifaire {cle!r} introuvable",
        )
    return tarif


@router.post("/reset/{poste_numero}", response_model=ResetPosteResponse)
def reset_poste_to_defaults(
    poste_numero: int = Path(ge=1, le=7),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Restaure les valeurs initiales (seed CSV) d'un poste pour l'entreprise
    du user. Cas-test figé : reset poste 3 → V1b retombe à 1 921,09 € EXACT
    (compte demo)."""
    n_reset = crud.reset_poste_to_seed_defaults(
        db, poste_numero, user.entreprise_id
    )
    return ResetPosteResponse(poste_numero=poste_numero, n_reset=n_reset)
