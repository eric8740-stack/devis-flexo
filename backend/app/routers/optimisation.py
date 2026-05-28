"""Router /api/optimisation — Sprint 13 Lot S13.D.7b + Sprint 14 Lot 2.

Endpoints :
  - POST /api/optimisation/calculer (Sprint 13.D)
        Moteur d'optimisation pose 6 règles métier + scoring sophistiqué.
  - POST /api/optimisation/matcher-outil (Sprint 14 Lot 2)
        Matching simple des cylindres parc tenant contre un brief client.

Activé pour les users avec module FlexoCompare (require_module).
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_module
from app.models import (
    CylindreMagnetique,
    Entreprise,
    Machine,
    MachineImprimerie,
    Matiere,
    OptionFabrication,
    User,
)
from app.schemas.matiere import MatiereOut
from app.schemas.optimisation import (
    MatcherOutilIn,
    MatcherOutilOut,
    MatchOutilOut,
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
from app.services.sens_metadata import (
    get_libelle_officiel,
    get_rotation_vue_a,
    get_rotation_vue_c,
)
from app.services.optimisation_loader import (
    OptimisationLoaderError,
    charger_baremes,
    charger_cylindres_actifs,
    charger_machines_actives,
    charger_options_par_codes,
)
from app.services.outil_matcher import ContrainteOutil, matcher_outils
from app.services.scope_service import get_or_404_scoped


router = APIRouter(prefix="/api/optimisation", tags=["optimisation"])


def _sens_int(sens_enroulement: str) -> int:
    """Convertit le code API ('SE0'..'SE9') vers l'entier (0..9).
    1-8 sont délégués à rotation_se ; 0 et 9 (bobines vierges sans
    impression) sont gérés par la façade sens_metadata."""
    return int(sens_enroulement.replace("SE", ""))


@router.get("/candidats/{id_candidat}/visuel")
def get_candidat_visuel(
    id_candidat: str,
    user: User = Depends(require_module("flexocompare")),
) -> dict:
    """Données visuelles d'un candidat — sens enroulement + rotations.

    Sprint 13 avenant (commit 3 PR B). Endpoint consommé par l'UI workflow
    3 étapes (PR C) au moment de l'affichage du visuel BAT par lot.

    L'`id_candidat` est un id composite encodé côté frontend, contenant a
    minima le sens d'enroulement en suffixe sous la forme `...-SE<n>`
    (ex: `12-3-2x5-SE1`). Le sens est la seule donnée nécessaire pour
    déterminer les rotations (les autres champs cylindre/machine/poses
    ne changent pas les rotations).

    SACRED : rotations issues de `app/services/rotation_se.py` (single
    source of truth).
    """
    try:
        sens_code = id_candidat.rsplit("-", 1)[-1]
        if not sens_code.startswith("SE"):
            raise ValueError("préfixe sens manquant")
        sens_int = int(sens_code[2:])
        if not 0 <= sens_int <= 9:
            raise ValueError("sens hors plage 0-9")
    except (ValueError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"id_candidat invalide ({id_candidat}). Format attendu : "
                "'<cyl>-<mach>-<dev>x<laize>-SE<n>' avec 0 ≤ n ≤ 9."
            ),
        ) from exc
    return {
        "id_candidat": id_candidat,
        "sens_enroulement": sens_code,
        "sens_enroulement_libelle": get_libelle_officiel(sens_int),
        "rotation_vue_a_deg": get_rotation_vue_a(sens_int),
        "rotation_vue_c_deg": get_rotation_vue_c(sens_int),
    }


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
    # === Matière : vérif scope AVANT toute autre logique (sécurité d'abord) ===
    matiere_obj: Matiere | None = None
    epaisseur_catalogue_um: int | None = None
    matiere_transparente_finale = payload.matiere_est_transparente
    if payload.matiere_id is not None:
        matiere_obj = (
            db.query(Matiere)
            .filter(
                Matiere.id == payload.matiere_id,
                Matiere.entreprise_id == user.entreprise_id,
            )
            .first()
        )
        if matiere_obj is None:
            # Anti-énumération multi-tenant : 404 si pas du tenant.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matière introuvable",
            )
        epaisseur_catalogue_um = matiere_obj.epaisseur_microns
        # La transparence devient automatiquement celle de la matière (la valeur
        # `matiere_est_transparente` du payload est ignorée si une matière est
        # sélectionnée, par contrat UI : champ read-only quand select dispo).
        matiere_transparente_finale = matiere_obj.est_transparent

    # Épaisseur appliquée : forçage > catalogue > legacy payload epaisseur_um
    forcage_epaisseur = payload.epaisseur_matiere_force_um is not None
    if forcage_epaisseur:
        epaisseur_appliquee_um = int(payload.epaisseur_matiere_force_um)  # type: ignore[arg-type]
    elif epaisseur_catalogue_um is not None:
        epaisseur_appliquee_um = int(epaisseur_catalogue_um)
    else:
        epaisseur_appliquee_um = int(payload.epaisseur_matiere_um)

    # Intervalle dev "recommandé" = ce que le moteur aurait choisi sans forçage
    # (max imprimeur / client). Sert d'écho de souveraineté pour le frontend.
    intervalle_dev_recommande = max(
        payload.intervalle_dev_min_mm,
        payload.contrainte_client.intervalle_dev_min_mm,
    )
    forcage_intervalle_dev = payload.intervalle_dev_force_mm is not None

    # Logique moteur :
    #  - Pas de forçage → on passe les valeurs natives, le moteur gère le
    #    message contrainte_client et choisit le max imprimeur/client.
    #  - Forçage → on impose la valeur en plancher imprimeur ET on neutralise
    #    la contrainte client pour s'assurer que le moteur applique cette
    #    valeur (et seulement celle-ci).
    if forcage_intervalle_dev:
        moteur_intervalle_dev_min = float(payload.intervalle_dev_force_mm)  # type: ignore[arg-type]
        moteur_contrainte_client = ContrainteClient(intervalle_dev_min_mm=0.0)
        intervalle_dev_applique = moteur_intervalle_dev_min
    else:
        moteur_intervalle_dev_min = payload.intervalle_dev_min_mm
        moteur_contrainte_client = ContrainteClient(
            intervalle_dev_min_mm=payload.contrainte_client.intervalle_dev_min_mm
        )
        intervalle_dev_applique = intervalle_dev_recommande

    # === Chargement catalogue tenant (options, cylindres, machines, barèmes) ===
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
        intervalle_dev_min_mm=moteur_intervalle_dev_min,
        nb_couleurs_impression=payload.nb_couleurs_impression,
        quantite=payload.quantite,
        matiere_est_transparente=matiere_transparente_finale,
        options=options_dc,
        cylindres=cylindres,
        machines=machines,
        bareme_echenillage=baremes["echenillage"],
        bareme_effet_banane=baremes["effet_banane"],
        bareme_compensation=baremes["compensation_laize_dev"],
        bareme_confort_roulage=baremes["confort_roulage"],
        contrainte_client=moteur_contrainte_client,
        nb_poses_laize_force=payload.nb_poses_laize_force,
    )

    out = optimiser_pose(inp)

    # === Enrichissement BAT du top 3 ====================================
    entreprise = db.query(Entreprise).filter_by(id=user.entreprise_id).one()
    z_par_cyl = {c.id: float(c.developpe_mm) for c in
                 db.query(CylindreMagnetique)
                 .filter_by(entreprise_id=user.entreprise_id, actif=True)
                 .all()}
    nom_par_machine = {m.id: m.nom for m in
                       db.query(MachineImprimerie)
                       .filter_by(entreprise_id=user.entreprise_id, actif=True)
                       .all()}
    chute_min = float(entreprise.chute_laterale_min_mm)
    palier = entreprise.palier_laize_papier_mm
    marge_liner = float(entreprise.marge_liner_mm)

    matiere_out = (
        MatiereOut.model_validate(matiere_obj) if matiere_obj is not None else None
    )

    configurations_out: list[OptimisationConfigOut] = []
    for c in out.configurations:
        # Intervalle laize : recommandé par le moteur vs forcé par l'utilisateur
        intervalle_laize_recommande = float(c.intervalle_laize_reel_mm)
        forcage_intervalle_laize = payload.intervalle_laize_force_mm is not None
        intervalle_laize_applique = (
            float(payload.intervalle_laize_force_mm)  # type: ignore[arg-type]
            if forcage_intervalle_laize
            else intervalle_laize_recommande
        )

        # Lacets : symétriques par défaut (intervalle_laize_applique / 2),
        # asymétriques si l'utilisateur les a explicitement forcés.
        if payload.lacets_asymetriques and payload.lacet_droit_mm is not None and payload.lacet_gauche_mm is not None:
            lacet_droit = float(payload.lacet_droit_mm)
            lacet_gauche = float(payload.lacet_gauche_mm)
        else:
            moitie = intervalle_laize_applique / 2
            lacet_droit = moitie
            lacet_gauche = moitie

        configurations_out.append(
            _to_config_out(
                c=c,
                z_cyl_mm=z_par_cyl.get(c.cylindre_id, 0.0),
                noms_machines=[
                    nom_par_machine.get(mid, f"#{mid}")
                    for mid in c.machines_compatibles
                ],
                quantite=payload.quantite,
                laize_etiq_mm=payload.format.largeur_mm,
                dev_etiq_mm=payload.format.hauteur_mm,
                chute_min_mm=chute_min,
                palier_mm=palier,
                marge_liner_mm=marge_liner,
                mandrin_mm=payload.mandrin_mm,
                epaisseur_matiere_um=float(epaisseur_appliquee_um),
                sens_enroulement=payload.sens_enroulement,
                # Souveraineté + lacets
                intervalle_laize_recommande_mm=intervalle_laize_recommande,
                intervalle_laize_applique_mm=intervalle_laize_applique,
                forcage_intervalle_laize=forcage_intervalle_laize,
                motif_forcage_intervalle_laize=payload.motif_forcage_intervalle_laize,
                intervalle_dev_recommande_mm=intervalle_dev_recommande,
                intervalle_dev_applique_mm=intervalle_dev_applique,
                forcage_intervalle_dev=forcage_intervalle_dev,
                motif_forcage_intervalle_dev=payload.motif_forcage_intervalle_dev,
                lacet_droit_mm=lacet_droit,
                lacet_gauche_mm=lacet_gauche,
                lacets_asymetriques=payload.lacets_asymetriques,
                matiere_out=matiere_out,
                epaisseur_appliquee_um=epaisseur_appliquee_um,
                forcage_epaisseur=forcage_epaisseur,
                motif_forcage_epaisseur=payload.motif_forcage_epaisseur,
            )
        )

    # === Warnings non bloquants (souveraineté commerciale) =================
    # Le forçage intervalle laize ne lève plus 422 même hors recommandation
    # moteur / sans motif : on calcule quand même et on remonte un message
    # explicite à afficher en bandeau orange UI. Les vrais blocages (valeur
    # 0 / négative / > 50) restent rejetés en 422 par Pydantic (gt=0, le=50).
    warnings: list[str] = []
    if payload.intervalle_laize_force_mm is not None:
        force_val = float(payload.intervalle_laize_force_mm)
        # Recommandation moteur top-1 si dispo : indicatif, varie par config.
        if configurations_out:
            reco_top1 = configurations_out[0].intervalle_laize_recommande_mm
            warnings.append(
                f"Intervalle laize forcé à {force_val:g} mm — le moteur "
                f"aurait recommandé {reco_top1:g} mm pour la configuration "
                f"top 1."
            )
        else:
            warnings.append(
                f"Intervalle laize forcé à {force_val:g} mm — valeur hors "
                f"recommandation moteur."
            )
        motif_norm = (payload.motif_forcage_intervalle_laize or "").strip()
        if len(motif_norm) < 10:
            warnings.append(
                "Motif de forçage intervalle laize manquant ou trop court "
                "(< 10 caractères) — pense à le renseigner pour la "
                "traçabilité commerciale."
            )

    return OptimisationCalculerResponse(
        configurations=configurations_out,
        nb_candidats=out.nb_candidats,
        message_filtrage=out.message_filtrage,
        intervalle_dev_min_applique_mm=out.intervalle_dev_min_applique_mm,
        message_contrainte_client=out.message_contrainte_client,
        warnings=warnings,
    )


def _to_config_out(
    *,
    c: ConfigurationPose,
    z_cyl_mm: float,
    noms_machines: list[str],
    quantite: int,
    laize_etiq_mm: float,
    dev_etiq_mm: float,
    chute_min_mm: float,
    palier_mm: int,
    marge_liner_mm: float,
    mandrin_mm: int,
    epaisseur_matiere_um: float,
    sens_enroulement: str,
    # Souveraineté commerciale + lacets
    intervalle_laize_recommande_mm: float,
    intervalle_laize_applique_mm: float,
    forcage_intervalle_laize: bool,
    motif_forcage_intervalle_laize: str | None,
    intervalle_dev_recommande_mm: float,
    intervalle_dev_applique_mm: float,
    forcage_intervalle_dev: bool,
    motif_forcage_intervalle_dev: str | None,
    lacet_droit_mm: float,
    lacet_gauche_mm: float,
    lacets_asymetriques: bool,
    matiere_out: MatiereOut | None,
    epaisseur_appliquee_um: int,
    forcage_epaisseur: bool,
    motif_forcage_epaisseur: str | None,
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
    # Nomenclature ICE : développé physique → nombre de dents (1 dent = 3.175 mm).
    # Arrondi à l'entier car les cylindres réels sont fabriqués au nombre de
    # dents entier ; les valeurs catalogue ICE (72, 80, 104, etc.) sont toujours
    # exactement reproductibles.
    nb_dents = round(z_cyl_mm / 3.175) if z_cyl_mm > 0 else 0

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
        nb_dents_cylindre=nb_dents,
        ml_total_m=round(ml_total, 2),
        m2_consomme=round(m2, 2),
        rendement_pct=round(rendement, 2),
        diametre_bobine_mm=diametre,
        laize_liner_mm=round(laize_liner, 2),
        sens_enroulement=sens_enroulement,  # type: ignore[arg-type]
        sens_enroulement_libelle=get_libelle_officiel(_sens_int(sens_enroulement)),
        rotation_vue_a_deg=get_rotation_vue_a(_sens_int(sens_enroulement)),
        rotation_vue_c_deg=get_rotation_vue_c(_sens_int(sens_enroulement)),
        machines_compatibles=list(c.machines_compatibles),
        noms_machines_compatibles=noms_machines,
        # Brief #28 : badge informationnel petit cylindre (UI étape 2).
        petit_cylindre=c.petit_cylindre,
        # Souveraineté commerciale + lacets
        intervalle_laize_recommande_mm=round(intervalle_laize_recommande_mm, 2),
        intervalle_laize_applique_mm=round(intervalle_laize_applique_mm, 2),
        forcage_intervalle_laize=forcage_intervalle_laize,
        motif_forcage_intervalle_laize=motif_forcage_intervalle_laize,
        intervalle_dev_recommande_mm=round(intervalle_dev_recommande_mm, 2),
        intervalle_dev_applique_mm=round(intervalle_dev_applique_mm, 2),
        forcage_intervalle_dev=forcage_intervalle_dev,
        motif_forcage_intervalle_dev=motif_forcage_intervalle_dev,
        lacet_droit_mm=round(lacet_droit_mm, 2),
        lacet_gauche_mm=round(lacet_gauche_mm, 2),
        lacets_asymetriques=lacets_asymetriques,
        matiere=matiere_out,
        epaisseur_appliquee_um=int(epaisseur_appliquee_um),
        forcage_epaisseur=forcage_epaisseur,
        motif_forcage_epaisseur=motif_forcage_epaisseur,
    )


# ---------------------------------------------------------------------------
# Sprint 14 Lot 2 — POST /api/optimisation/matcher-outil
# ---------------------------------------------------------------------------


@router.post("/matcher-outil", response_model=MatcherOutilOut)
def post_matcher_outil(
    body: MatcherOutilIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_module("flexocompare")),
) -> MatcherOutilOut:
    """Match les cylindres du parc tenant contre un brief client.

    Distinct du moteur d'optimisation pose `/calculer` (Sprint 13.D, 6 règles
    métier + scoring sophistiqué) : ici on fait un matching simple
    nb_dents × pas_chenille → poses possibles, score = surface utile /
    surface développée machine. Sert au funnel d'entrée Sprint 14 où le
    commercial saisit un brief client et veut voir d'abord si un outil
    existant convient avant de chiffrer.

    Scope tenant strict : machine_id et cylindres viennent obligatoirement
    de `user.entreprise_id` ; tout cross-tenant → 404 (anti-énumération).

    Utilise le modèle `Machine` (table `machine` Sprint 2) — cohérent avec
    le sacred `cylindre_matcher.py` Sprint 7 qui consomme `Machine.laize_max_mm`.
    `MachineImprimerie` (Sprint 13.B) reste réservé au moteur d'optimisation
    pose `/calculer`.
    """
    # 1) Récupère la machine scopée (404 si cross-tenant)
    machine = get_or_404_scoped(db, Machine, body.machine_id, user)

    # 2) Charge les cylindres actifs du tenant (raw query — pas le loader
    #    Sprint 13 qui mappe en dataclass Cylindre ; ici on a besoin du
    #    modèle ORM pour passer au service avec `.id` et `.developpe_mm`).
    cylindres = (
        db.query(CylindreMagnetique)
        .filter_by(entreprise_id=user.entreprise_id, actif=True)
        .all()
    )

    # 3) Construit la contrainte et appelle le service stateless
    contrainte = ContrainteOutil(
        laize_etiquette_mm=body.laize_etiquette_mm,
        dev_etiquette_mm=body.dev_etiquette_mm,
        intervalle_dev_mm=body.intervalle_dev_mm,
        intervalle_laize_mm=body.intervalle_laize_mm,
        laize_machine_mm=Decimal(str(machine.laize_max_mm)),
        nb_fronts_min=body.nb_fronts_min,
        nb_fronts_max=body.nb_fronts_max,
    )
    matches = matcher_outils(contrainte, cylindres)

    return MatcherOutilOut(
        matches=[
            MatchOutilOut(
                cylindre_id=m.cylindre_id,
                nb_dents=m.nb_dents,
                developpe_mm=m.developpe_mm,
                nb_poses_dev=m.nb_poses_dev,
                nb_poses_laize=m.nb_poses_laize,
                nb_poses_total=m.nb_poses_total,
                cout_outil_eur=m.cout_outil_eur,
                score_efficacite=m.score_efficacite,
            )
            for m in matches
        ],
        nb_matches=len(matches),
    )
