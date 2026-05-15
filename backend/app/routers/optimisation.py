"""Router /api/optimisation — Sprint 13 Lot S13.D.7b.

1 endpoint :
  - POST /api/optimisation/calculer
        Reçoit le contexte devis (format, couleurs, options, contrainte
        client) + hydrate cylindres/machines/barèmes du tenant + appelle
        optimiser_pose(). Renvoie top 3 (≤ 3) configs + métadonnées.

Activé pour les users avec module FlexoCompare (require_module).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_module
from app.models import User
from app.schemas.optimisation import (
    OptimisationCalculerRequest,
    OptimisationCalculerResponse,
    OptimisationConfigOut,
)
from app.services.optimisation.moteur import optimiser_pose
from app.services.optimisation.types import (
    ContrainteClient,
    Format,
    OptimisationInput,
)
from app.services.optimisation_loader import (
    OptimisationLoaderError,
    charger_baremes,
    charger_cylindres_actifs,
    charger_machines_actives,
    charger_options_par_codes,
)


router = APIRouter(prefix="/api/optimisation", tags=["optimisation"])


@router.post("/calculer", response_model=OptimisationCalculerResponse)
def post_calculer(
    payload: OptimisationCalculerRequest,
    user: User = Depends(require_module("flexocompare")),
    db: Session = Depends(get_db),
) -> OptimisationCalculerResponse:
    """Calcule le top 3 configurations de pose pour le devis donné."""
    try:
        options_dc = charger_options_par_codes(
            db, user.entreprise_id, payload.options_codes
        )
    except OptimisationLoaderError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    cylindres = charger_cylindres_actifs(db, user.entreprise_id)
    machines = charger_machines_actives(db, user.entreprise_id)
    baremes = charger_baremes(db, user.entreprise_id)

    if not cylindres or not machines:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Aucun cylindre ou machine actif dans votre catalogue. "
                "Avez-vous complété l'onboarding ?"
            ),
        )

    inp = OptimisationInput(
        format=Format(
            hauteur_mm=payload.format.hauteur_mm,
            largeur_mm=payload.format.largeur_mm,
            rayon_angles_mm=payload.format.rayon_angles_mm,
            forme_courbe=payload.format.forme_courbe,
        ),
        intervalle_dev_min_mm=payload.intervalle_dev_min_mm,
        nb_couleurs_impression=payload.nb_couleurs_impression,
        quantite=payload.quantite,
        matiere_est_transparente=payload.matiere_est_transparente,
        options=options_dc,
        cylindres=cylindres,
        machines=machines,
        bareme_echenillage=baremes["echenillage"],
        bareme_effet_banane=baremes["effet_banane"],
        bareme_compensation=baremes["compensation_laize_dev"],
        bareme_confort_roulage=baremes["confort_roulage"],
        contrainte_client=ContrainteClient(
            intervalle_dev_min_mm=payload.contrainte_client.intervalle_dev_min_mm
        ),
    )

    out = optimiser_pose(inp)

    return OptimisationCalculerResponse(
        configurations=[
            OptimisationConfigOut(
                cylindre_id=c.cylindre_id,
                machine_id=c.machine_id,
                nb_poses_dev=c.nb_poses_dev,
                nb_poses_laize=c.nb_poses_laize,
                nb_poses_total=c.nb_poses_total,
                intervalle_dev_reel_mm=c.intervalle_dev_reel_mm,
                intervalle_laize_reel_mm=c.intervalle_laize_reel_mm,
                largeur_plaque_mm=c.largeur_plaque_mm,
                z_mini_effet_banane=c.z_mini_effet_banane,
                qualite_echenillage=c.qualite_echenillage,
                consolidation_atteinte=c.consolidation_atteinte,
                intervalle_laize_souhaitable_mm=c.intervalle_laize_souhaitable_mm,
                disposition_poses=c.disposition_poses,
                coef_vitesse_echenillage=c.coef_vitesse_echenillage,
                coef_gache_echenillage=c.coef_gache_echenillage,
                coef_confort_rayon=c.coef_confort_rayon,
                coef_quinconce=c.coef_quinconce,
                coef_consolidation=c.coef_consolidation,
                coef_vitesse_options=c.coef_vitesse_options,
                coef_gache_options=c.coef_gache_options,
                coef_vitesse_final=c.coef_vitesse_final,
                coef_gache_final=c.coef_gache_final,
                score=round(c.score, 2),
            )
            for c in out.configurations
        ],
        nb_candidats=out.nb_candidats,
        message_filtrage=out.message_filtrage,
        intervalle_dev_min_applique_mm=out.intervalle_dev_min_applique_mm,
        message_contrainte_client=out.message_contrainte_client,
    )
