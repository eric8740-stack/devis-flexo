"""Router /api/onboarding — Sprint 13 Lot S13.C.2.

2 endpoints :
  - GET  /api/onboarding/catalogue-defaults
        Expose le catalogue figé (19 cyl + 3 machines + 30 matières +
        20 options + 4 barèmes) consommé par le tunnel d'onboarding 4 écrans.
        Authentifié (mais pas scopé tenant — le catalogue est le même
        pour tout le monde). N'exige PAS le module flexocompare car
        l'onboarding peut concerner les 2 modules à terme.

  - POST /api/onboarding/initialiser-catalogues
        Reçoit la sélection user + crée les rows en BDD scoped sur le
        tenant. Idempotence stricte : 409 si déjà initialisé (on ne veut
        pas créer des doublons silencieux).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.data.catalogue_defaults import (
    BAREMES_DEFAULT,
    CYLINDRES_STANDARD_MM,
    MACHINES_DEFAULT,
    MATIERES_DEFAULT,
    OPTIONS_FABRICATION_DEFAULT,
)
from app.db import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.onboarding import (
    OnboardingCatalogueDefaults,
    OnboardingInitRequest,
    OnboardingInitResponse,
)
from app.services.onboarding_service import (
    OnboardingError,
    has_existing_catalogue,
    initialiser_catalogues,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/catalogue-defaults", response_model=OnboardingCatalogueDefaults)
def get_catalogue_defaults(
    _: User = Depends(get_current_user),
) -> OnboardingCatalogueDefaults:
    """Renvoie le catalogue figé pour affichage du tunnel onboarding.

    Authentifié uniquement (pas de scope tenant nécessaire — c'est le
    même catalogue pour tous les utilisateurs).
    """
    return OnboardingCatalogueDefaults(
        cylindres_developpes_mm=list(CYLINDRES_STANDARD_MM),
        machines=MACHINES_DEFAULT,
        matieres=MATIERES_DEFAULT,
        options=OPTIONS_FABRICATION_DEFAULT,
        baremes=BAREMES_DEFAULT,
    )


@router.get("/status")
def get_onboarding_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Indique au frontend si le tenant a déjà été onboardé.

    Heuristique simple : présence d'au moins une row dans l'une des 5
    tables S13.B scopées tenant (cylindres, machines, matières, options
    scoped, barèmes). Utilisé par le layout Next.js pour rediriger vers
    /onboarding au login si besoin.
    """
    initialise = has_existing_catalogue(db, user.entreprise_id)
    return {"catalogue_initialise": initialise}


@router.post(
    "/initialiser-catalogues",
    response_model=OnboardingInitResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_initialiser_catalogues(
    payload: OnboardingInitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingInitResponse:
    """Initialise les catalogues du tenant à partir de la sélection user.

    409 si déjà initialisé. 422 si un code envoyé n'existe pas dans le
    catalogue par défaut. 201 sinon avec les compteurs.
    """
    try:
        counts = initialiser_catalogues(
            db=db,
            entreprise_id=user.entreprise_id,
            cylindres_developpes_mm=payload.cylindres_developpes_mm,
            machines_codes=payload.machines_codes,
            matieres_codes=payload.matieres_codes,
            options_codes=payload.options_codes,
        )
    except OnboardingError as exc:
        # On distingue "déjà initialisé" (409) de "code inconnu" (422)
        # par contenu du message — pas idéal, on pourrait sous-classer
        # mais ça ferait du sur-engineering pour 1 cas chacun.
        msg = str(exc)
        if msg.startswith("Catalogue déjà initialisé"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg
        ) from exc

    return OnboardingInitResponse(
        cylindres=counts["cylindres"],
        machines=counts["machines"],
        matieres=counts["matieres"],
        options=counts["options"],
        baremes=counts["baremes"],
        total=sum(counts.values()),
    )
