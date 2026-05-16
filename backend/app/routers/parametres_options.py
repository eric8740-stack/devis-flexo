"""Router /api/parametres/options-fabrication — CRUD tenant.

4 endpoints (cf. CdC "Paramètres > Options de fabrication") :
  - GET    /api/parametres/options-fabrication
        List des options scopées tenant (n'inclut PAS le catalogue global
        entreprise_id=NULL — c'est la liste éditable de l'imprimeur).

  - POST   /api/parametres/options-fabrication/from-master/{code}
        Active une option du catalogue master Sprint 13 sur le tenant
        courant. Copie les coefs/modules requis, snapshot le master dans
        `valeur_recommandee_origine`. 404 si code inconnu, 409 si déjà
        activé.

  - PATCH  /api/parametres/options-fabrication/{id}
        Édite coefs vitesse/gâche, tarification, et flag actif. 404 si
        l'option n'appartient pas au tenant. `valeur_recommandee_origine`
        n'est jamais modifié (référence figée).

  - DELETE /api/parametres/options-fabrication/{id}
        Soft delete : positionne actif=False. La row reste en base pour
        ne pas casser les devis qui la référencent.

Activé pour les users avec module FlexoCompare (les options de fabrication
n'ont de sens qu'avec le moteur d'optimisation).
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.data.catalogue_defaults import OPTIONS_FABRICATION_DEFAULT
from app.db import get_db
from app.dependencies import require_module
from app.models import OptionFabrication, User
from app.schemas.parametres_options import (
    OptionFabricationTenantOut,
    OptionFabricationUpdate,
)
from app.services.scope_service import get_or_404_scoped, scope_to_entreprise


router = APIRouter(
    prefix="/api/parametres/options-fabrication",
    tags=["parametres-options"],
)


def _snapshot_recommande(master: dict) -> dict:
    """Capture, depuis OPTIONS_FABRICATION_DEFAULT, les valeurs qui servent
    à afficher des hints "(recommandé : X.XX)" dans le dialog d'édition."""
    return {
        "coef_vitesse_impact": float(master.get("coef_vitesse_impact", 1.0)),
        "coef_gache_impact": float(master.get("coef_gache_impact", 1.0)),
        "ajoute_temps_calage_min": int(master.get("ajoute_temps_calage_min", 0)),
    }


@router.get("", response_model=list[OptionFabricationTenantOut])
def list_options_tenant(
    user: User = Depends(require_module("flexocompare")),
    db: Session = Depends(get_db),
) -> list[OptionFabricationTenantOut]:
    """Liste les options de fabrication scopées tenant, triées catégorie/libellé.

    N'expose que les rows entreprise_id == user.entreprise_id (pas le
    catalogue global) — c'est la liste éditable de l'imprimeur, pas la
    liste consommable du moteur (cette dernière passe par
    `/api/optimisation/options-disponibles`).
    """
    rows = (
        scope_to_entreprise(
            db.query(OptionFabrication), OptionFabrication, user
        )
        .order_by(OptionFabrication.categorie, OptionFabrication.libelle)
        .all()
    )
    return [OptionFabricationTenantOut.model_validate(r) for r in rows]


@router.post(
    "/from-master/{code}",
    response_model=OptionFabricationTenantOut,
    status_code=status.HTTP_201_CREATED,
)
def create_from_master(
    code: str,
    user: User = Depends(require_module("flexocompare")),
    db: Session = Depends(get_db),
) -> OptionFabricationTenantOut:
    """Active l'option `code` du catalogue master Sprint 13 sur le tenant.

    404 si `code` n'existe pas dans le catalogue master.
    409 si une option avec ce code existe déjà pour ce tenant.
    """
    master = next(
        (o for o in OPTIONS_FABRICATION_DEFAULT if o["code"] == code), None
    )
    if master is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Code option '{code}' inconnu dans le catalogue master.",
        )

    existing = (
        db.query(OptionFabrication)
        .filter(
            OptionFabrication.entreprise_id == user.entreprise_id,
            OptionFabrication.code == code,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Option '{code}' déjà activée pour votre entreprise. "
                "Utilisez l'écran d'édition pour la réactiver si nécessaire."
            ),
        )

    row = OptionFabrication(
        entreprise_id=user.entreprise_id,
        code=master["code"],
        libelle=master["libelle"],
        categorie=master.get("categorie"),
        description=master.get("description"),
        ajoute_cliches=int(master.get("ajoute_cliches", 0)),
        ajoute_couleurs=int(master.get("ajoute_couleurs", 0)),
        ajoute_outils_decoupe=int(master.get("ajoute_outils_decoupe", 0)),
        groupes_couleurs_requis=int(master.get("groupes_couleurs_requis", 0)),
        modules_speciaux_requis=list(master.get("modules_speciaux_requis", []))
        or None,
        est_silhouette_auto=bool(master.get("est_silhouette_auto", False)),
        ajoute_temps_calage_min=int(master.get("ajoute_temps_calage_min", 0)),
        coef_vitesse_impact=Decimal(
            str(master.get("coef_vitesse_impact", "1.00"))
        ),
        coef_gache_impact=Decimal(str(master.get("coef_gache_impact", "1.00"))),
        actif=True,
        valeur_recommandee_origine=_snapshot_recommande(master),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return OptionFabricationTenantOut.model_validate(row)


@router.patch("/{option_id}", response_model=OptionFabricationTenantOut)
def update_option(
    option_id: int,
    payload: OptionFabricationUpdate,
    user: User = Depends(require_module("flexocompare")),
    db: Session = Depends(get_db),
) -> OptionFabricationTenantOut:
    """Édite les champs paramétrables d'une option tenant.

    404 si l'option n'appartient pas au tenant. `valeur_recommandee_origine`
    n'est pas touchée (référence figée).
    """
    row = get_or_404_scoped(db, OptionFabrication, option_id, user)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return OptionFabricationTenantOut.model_validate(row)


@router.delete("/{option_id}", response_model=OptionFabricationTenantOut)
def soft_delete_option(
    option_id: int,
    user: User = Depends(require_module("flexocompare")),
    db: Session = Depends(get_db),
) -> OptionFabricationTenantOut:
    """Soft delete : positionne actif=False. La row reste en base pour ne
    pas casser les devis historiques qui la référencent. Pour réactiver,
    utiliser PATCH avec `{"actif": true}`.
    """
    row = get_or_404_scoped(db, OptionFabrication, option_id, user)
    row.actif = False
    db.commit()
    db.refresh(row)
    return OptionFabricationTenantOut.model_validate(row)
