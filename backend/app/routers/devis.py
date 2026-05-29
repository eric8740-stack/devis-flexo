"""Router HTTP /api/devis (Sprint 4 Lot 4b, S12-C scoped).

6 endpoints CRUD + 1 duplicate + 1 PDF. Chaque endpoint scope par
`user.entreprise_id` via `Depends(get_current_user)`.
"""
import math
from dataclasses import asdict
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.crud import devis as crud
from app.db import get_db
from app.dependencies import get_current_user
from app.models import Devis, MachineRebobineuse, ParametreMandrin, User
from app.schemas.devis_persist import (
    CoherenceBobineRequest,
    CoherenceBobineResponse,
    DevisCreate,
    DevisDetail,
    DevisListResponse,
    DevisUpdate,
    PlanBobinesSelectionIn,
    PlanBobinesSelectionOut,
    PlanificateurBobinesRequest,
    PlanificateurBobinesResponse,
    PreviewCoutsIn,
    PreviewCoutsOut,
)
from app.services.coherence_bobine import evaluer_coherence_bobine
from app.services.planificateur_bobines import calculer_plan_bobines
from app.services.rebobinage.types import (
    MachineRebobinageParams,
    ParametresMandrinRuntime,
    TarifsMandrins,
)
from app.services.pdf_service import generate_devis_pdf
from app.services.scope_service import get_or_404_scoped

router = APIRouter(prefix="/api/devis", tags=["devis"])


@router.post(
    "/preview-couts",
    response_model=PreviewCoutsOut,
)
def preview_couts_devis(
    payload: PreviewCoutsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PreviewCoutsOut:
    """Brief #33 — recalcul live des coûts sans persister.

    Utilisé par l'étape 4 chiffrage UI pour rafraîchir le récap brut/net
    à chaque toggle d'option ou ajustement de marge/réduction, sans
    créer un devis.

    Multi-tenant strict via `user.entreprise_id`. Aucune mutation DB
    (les LotProduction transitoires construits ne sont pas db.add).
    """
    lots_data = [lot.model_dump() for lot in payload.lots]
    result = crud.preview_couts_multilots(
        db,
        entreprise_id=user.entreprise_id,
        lots_data=lots_data,
        payload_input=payload.payload_input,
        reduction_pct=payload.reduction_pct,
        # Sprint 16 fix chiffrage : propage les compteurs couleurs (P2 Encres).
        nb_couleurs_par_type=crud._mapper_nb_couleurs(payload.nb_couleurs),
    )
    return PreviewCoutsOut(**result)


@router.get("", response_model=DevisListResponse)
def list_devis(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche numéro ou nom client"),
    statut: Literal["brouillon", "valide"] | None = Query(None),
    sort: Literal["date_desc", "date_asc", "numero_asc", "ht_desc"] = Query(
        "date_desc"
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items, total = crud.list_devis(
        db,
        entreprise_id=user.entreprise_id,
        page=page,
        per_page=per_page,
        search=search,
        statut=statut,
        sort=sort,
    )
    pages = max(1, math.ceil(total / per_page)) if total else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get("/{devis_id}", response_model=DevisDetail)
def get_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    return crud.get_devis(db, devis_id)


@router.post("", response_model=DevisDetail, status_code=status.HTTP_201_CREATED)
def create_devis(
    payload: DevisCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return crud.create_devis(db, payload, entreprise_id=user.entreprise_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Champ payload manquant : {exc.args[0]}",
        ) from exc


@router.put("/{devis_id}", response_model=DevisDetail)
def update_devis(
    devis_id: int,
    payload: DevisUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    try:
        return crud.update_devis(db, devis_id, payload)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc) if isinstance(exc, ValueError) else f"Champ payload manquant : {exc.args[0]}",
        ) from exc


@router.delete("/{devis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    crud.delete_devis(db, devis_id)


@router.post(
    "/{devis_id}/duplicate",
    response_model=DevisDetail,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_or_404_scoped(db, Devis, devis_id, user)
    return crud.duplicate_devis(db, devis_id)


@router.get("/{devis_id}/pdf")
def download_devis_pdf(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Génère le PDF du devis et le retourne en téléchargement.

    Lot 4f : nom de fichier = {numero}.pdf (Content-Disposition attachment).
    Le service PDF (Lot 4e) lit weasyprint en lazy import — sur Linux
    Docker prod, les libs natives sont installées via Dockerfile.
    """
    get_or_404_scoped(db, Devis, devis_id, user)
    devis = crud.get_devis(db, devis_id)
    pdf_bytes = generate_devis_pdf(devis, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{devis.numero}.pdf"'
        },
    )


@router.post(
    "/planificateur-bobines",
    response_model=PlanificateurBobinesResponse,
    status_code=status.HTTP_200_OK,
)
def planificateur_bobines(
    payload: PlanificateurBobinesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanificateurBobinesResponse:
    """3 (ou 4) scénarios de découpe en bobines pour le rapport de fab.

    Endpoint stateless (zéro écriture DB) consommé par le composant
    « Plan de bobines » sur `/devis/[id]`. Calculs géométriques via
    `bat_calculs` (SSOT CC2, helpers déjà mergés) — zéro duplication.

    Coût rebobinage en LECTURE SEULE des helpers existants
    (`arbitrage_mandrins` + `calcul_temps`) : on passe `nb_bobines` au
    moteur, on lit le coût. Aucune modification de logique métier.

    Si `machine_rebobineuse_id` ou `tarifs_mandrins` manquent → scénarios
    renvoyés sans coût et `recommande_cle = None` (UI affiche géométrie
    seule, sans badge recommandé).
    """
    machine_params: MachineRebobinageParams | None = None
    parametres: ParametresMandrinRuntime | None = None
    tarifs_obj: TarifsMandrins | None = None

    if payload.machine_rebobineuse_id is not None:
        # Scope tenant : on refuse silencieusement (coût None) si la
        # rebobineuse n'appartient pas à ce tenant — UX moins brutale
        # qu'un 404 sur un endpoint « préview ».
        machine = (
            db.query(MachineRebobineuse)
            .filter(
                MachineRebobineuse.id == payload.machine_rebobineuse_id,
                MachineRebobineuse.entreprise_id == user.entreprise_id,
            )
            .one_or_none()
        )
        if machine is not None:
            machine_params = MachineRebobinageParams(
                vitesse_pratique_m_min=machine.vitesse_pratique_m_min,
                cout_horaire_eur=Decimal(machine.cout_horaire_eur),
                temps_changement_bobine_min=Decimal(
                    machine.temps_changement_bobine_min
                ),
            )
            # Snapshot runtime parametre_mandrin (scie_disponible).
            row = (
                db.query(ParametreMandrin)
                .filter(ParametreMandrin.entreprise_id == user.entreprise_id)
                .one_or_none()
            )
            parametres = ParametresMandrinRuntime(
                scie_disponible=bool(row.scie_disponible) if row else False,
            )

    if payload.tarifs_mandrins is not None:
        tarifs_obj = TarifsMandrins(
            prix_pre_coupe_par_mandrin_eur=payload.tarifs_mandrins.prix_pre_coupe_par_mandrin_eur,
            cout_decoupe_interne_par_mandrin_eur=payload.tarifs_mandrins.cout_decoupe_interne_par_mandrin_eur,
            cout_fixe_decoupe_interne_eur=payload.tarifs_mandrins.cout_fixe_decoupe_interne_eur,
        )

    try:
        result = calculer_plan_bobines(
            quantite_commandee=payload.quantite_commandee,
            n_laize=payload.n_laize,
            pas_mm=payload.pas_mm,
            mandrin_mm=payload.mandrin_mm,
            diametre_max_bobine_mm=payload.diametre_max_bobine_mm,
            epaisseur_matiere_um=payload.epaisseur_matiere_um,
            nb_etiq_impose=payload.nb_etiq_impose,
            nb_bobines_impose=payload.nb_bobines_impose,
            packaging_nb_etiq_par_bobine=payload.packaging_nb_etiq_par_bobine,
            machine=machine_params,
            tarifs=tarifs_obj,
            parametres=parametres,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input planificateur invalide : {exc}",
        ) from exc

    # asdict convertit récursivement le dataclass frozen + ses nested
    # (list[RepartitionBobine], AlerteImpose) en dict pur — Pydantic v2
    # valide proprement sans avoir besoin de `from_attributes=True` à
    # tous les niveaux. Les Decimal restent Decimal (cf. tests).
    return PlanificateurBobinesResponse.model_validate(asdict(result))


@router.put(
    "/{devis_id}/plan-bobines",
    response_model=PlanBobinesSelectionOut,
    status_code=status.HTTP_200_OK,
)
def update_plan_bobines(
    devis_id: int,
    payload: PlanBobinesSelectionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlanBobinesSelectionOut:
    """Persiste la sélection commerciale dans `payload_input.plan_bobines`.

    Écriture **ciblée** (merge partiel) : on ne touche QUE la sous-clé
    `plan_bobines`, le reste de `payload_input` (sens_enroulement,
    nb_couleurs, options_codes_etape4, mandrin_mm, etc.) est strictement
    préservé. C'est la raison pour laquelle on n'utilise pas le PUT
    générique /devis/{id} (qui setattr le bloc entier).

    Le forçage IMPOSE (`force_diametre=True`) exige un motif non vide
    (validation côté schema, 422 si manquant). Sans forçage, on
    persiste le scénario nominal.

    Tenant scopé : 404 si le devis n'appartient pas à l'entreprise.
    """
    devis = get_or_404_scoped(db, Devis, devis_id, user)

    # `payload_input` peut être None / pas un dict si devis legacy.
    # On normalise en dict pour pouvoir merger sans crash.
    payload_input = devis.payload_input
    if not isinstance(payload_input, dict):
        payload_input = {}

    # Merge ciblé : on REMPLACE la sous-clé `plan_bobines` uniquement.
    # Les autres clés (sens, couleurs, options, etc.) restent intactes.
    selection_dict = payload.model_dump(exclude_none=False)
    nouveau_payload_input = {**payload_input, "plan_bobines": selection_dict}

    # Réassignation explicite : SQLAlchemy ne détecte pas la mutation
    # d'un dict en place sur une colonne JSON. On change la référence.
    devis.payload_input = nouveau_payload_input
    db.commit()
    db.refresh(devis)

    return PlanBobinesSelectionOut(**selection_dict)


@router.post(
    "/coherence-bobine",
    response_model=CoherenceBobineResponse,
    status_code=status.HTTP_200_OK,
)
def check_coherence_bobine(
    payload: CoherenceBobineRequest,
    _: User = Depends(get_current_user),
) -> CoherenceBobineResponse:
    """Vérifie la cohérence Ø ext / nb étiquettes (saisie brief client).

    Endpoint stateless (zéro écriture DB) consommé en live par le
    formulaire — UX : alerte non bloquante sous les champs. Toutes les
    formules délèguent à `bat_calculs` (SSOT mm cohérente avec la VUE B
    et le 242 mm) ; aucune duplication frontend.
    """
    result = evaluer_coherence_bobine(
        diametre_ext_saisi_mm=payload.diametre_ext_saisi_mm,
        nb_etiq_saisi=payload.nb_etiq_saisi,
        mandrin_mm=payload.mandrin_mm,
        pas_mm=payload.pas_mm,
        epaisseur_catalogue_um=payload.epaisseur_catalogue_um,
        diametre_max_client_mm=payload.diametre_max_client_mm,
        tolerance_pct=payload.tolerance_pct,
    )
    return CoherenceBobineResponse(
        severity=result.severity,
        message=result.message,
        nb_max=result.nb_max,
        diametre_requis_mm=result.diametre_requis_mm,
        fit_severity=result.fit_severity,
        fit_message=result.fit_message,
        epaisseur_appliquee_um=result.epaisseur_appliquee_um,
        epaisseur_source=result.epaisseur_source,
    )
