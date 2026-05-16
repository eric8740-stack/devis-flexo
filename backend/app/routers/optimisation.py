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
from app.models import CylindreMagnetique, Entreprise, OptionFabrication, User
from app.schemas.optimisation import (
    OptimisationCalculerRequest,
    OptimisationCalculerResponse,
    OptimisationConfigOut,
    OptionDisponiblePublic,
)
from app.services.optimisation.bat_calculs import (
    calcul_chute_reelle_par_cote,
    calcul_diametre_bobine,
    calcul_laize_liner,
    calcul_laize_papier,
    calcul_laize_plaque,
    calcul_m2_consomme,
    calcul_ml_total,
    calcul_rendement,
)
from app.services.optimisation.moteur import optimiser_pose
from app.services.optimisation.types import (
    ConfigurationPose,
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


@router.get(
    "/options-disponibles",
    response_model=list[OptionDisponiblePublic],
)
def get_options_disponibles(
    user: User = Depends(require_module("flexocompare")),
    db: Session = Depends(get_db),
) -> list[OptionDisponiblePublic]:
    """Liste les options de fabrication réellement disponibles pour ce tenant.

    Renvoie l'union (options tenant + catalogue global) en privilégiant la
    version tenant si elle override un code global (cohérent avec
    `charger_options_par_codes`). Filtre `actif=True`. Trié par catégorie
    puis libellé pour un rendu UI stable.
    """
    rows = (
        db.query(OptionFabrication)
        .filter(OptionFabrication.actif.is_(True))
        .filter(
            (OptionFabrication.entreprise_id == user.entreprise_id)
            | (OptionFabrication.entreprise_id.is_(None))
        )
        .all()
    )

    by_code: dict[str, OptionFabrication] = {}
    for r in rows:
        existing = by_code.get(r.code)
        if existing is None or (
            existing.entreprise_id is None and r.entreprise_id is not None
        ):
            by_code[r.code] = r

    options = sorted(
        by_code.values(),
        key=lambda o: ((o.categorie or "").lower(), o.libelle.lower()),
    )
    return [
        OptionDisponiblePublic(
            id=o.id,
            code=o.code,
            libelle=o.libelle,
            categorie=o.categorie,
            coef_vitesse_impact=float(o.coef_vitesse_impact),
            coef_gache_impact=float(o.coef_gache_impact),
        )
        for o in options
    ]


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

    # PR #9.1 — enrichir chaque config du top 3 avec les calculs BAT.
    # On charge l'entreprise pour récupérer les 4 paramètres tenant
    # (chute, palier, marge_liner, refilage), et un index cyl_id → dev
    # pour retrouver Z (le moteur ne porte pas Z dans la config out).
    entreprise = db.query(Entreprise).filter_by(id=user.entreprise_id).one()
    z_par_cyl = {c.id: float(c.developpe_mm) for c in
                 db.query(CylindreMagnetique)
                 .filter_by(entreprise_id=user.entreprise_id, actif=True)
                 .all()}
    chute_min = float(entreprise.chute_laterale_min_mm)
    palier = entreprise.palier_laize_papier_mm
    marge_liner = float(entreprise.marge_liner_mm)

    configurations_out: list[OptimisationConfigOut] = []
    for c in out.configurations:
        configurations_out.append(
            _to_config_out(
                c=c,
                z_cyl_mm=z_par_cyl.get(c.cylindre_id, 0.0),
                quantite=payload.quantite,
                laize_etiq_mm=payload.format.largeur_mm,
                dev_etiq_mm=payload.format.hauteur_mm,
                chute_min_mm=chute_min,
                palier_mm=palier,
                marge_liner_mm=marge_liner,
                mandrin_mm=payload.mandrin_mm,
                epaisseur_matiere_um=payload.epaisseur_matiere_um,
                sens_enroulement=payload.sens_enroulement,
            )
        )

    return OptimisationCalculerResponse(
        configurations=configurations_out,
        nb_candidats=out.nb_candidats,
        message_filtrage=out.message_filtrage,
        intervalle_dev_min_applique_mm=out.intervalle_dev_min_applique_mm,
        message_contrainte_client=out.message_contrainte_client,
    )


def _to_config_out(
    *,
    c: ConfigurationPose,
    z_cyl_mm: float,
    quantite: int,
    laize_etiq_mm: float,
    dev_etiq_mm: float,
    chute_min_mm: float,
    palier_mm: int,
    marge_liner_mm: float,
    mandrin_mm: int,
    epaisseur_matiere_um: float,
    sens_enroulement: str,
) -> OptimisationConfigOut:
    """Map ConfigurationPose → OptimisationConfigOut avec champs BAT calculés."""
    laize_plaque = calcul_laize_plaque(
        c.nb_poses_laize, laize_etiq_mm, c.intervalle_laize_reel_mm
    )
    laize_papier = calcul_laize_papier(laize_plaque, chute_min_mm, palier_mm)
    chute_reelle = calcul_chute_reelle_par_cote(laize_papier, laize_plaque)
    ml_total = calcul_ml_total(quantite, c.nb_poses_dev, c.nb_poses_laize, z_cyl_mm)
    m2 = calcul_m2_consomme(ml_total, laize_papier)
    rendement = calcul_rendement(quantite, laize_etiq_mm, dev_etiq_mm, m2)
    diametre = calcul_diametre_bobine(
        ml_total, epaisseur_matiere_um, mandrin_mm, laize_papier
    )
    laize_liner = calcul_laize_liner(laize_etiq_mm, marge_liner_mm)

    return OptimisationConfigOut(
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
        # BAT
        laize_plaque_mm=round(laize_plaque, 2),
        laize_papier_mm=round(laize_papier, 2),
        chute_laterale_reelle_mm=round(chute_reelle, 2),
        z_cylindre_mm=round(z_cyl_mm, 2),
        ml_total_m=round(ml_total, 2),
        m2_consomme=round(m2, 2),
        rendement_pct=round(rendement, 2),
        diametre_bobine_mm=diametre,
        laize_liner_mm=round(laize_liner, 2),
        sens_enroulement=sens_enroulement,  # type: ignore[arg-type]
        machines_compatibles=list(c.machines_compatibles),
    )
