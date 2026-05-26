"""Router /api/rebobinage/* + /api/devis/{id}/rebobinage — Sprint 16 Lot C.

3 endpoints :

  POST   /api/rebobinage/calculer                 (preview — pas de persist)
  POST   /api/devis/{devis_id}/rebobinage         (apply — persist sur devis)
  DELETE /api/devis/{devis_id}/rebobinage         (retire la ligne)

Tous protégés par `Depends(get_current_user)` et scopés multi-tenant
via `user.entreprise_id`. Pas de `require_module(...)` : le rebobinage
fait partie du cœur devis flexo (comme `/api/devis`, `/api/optimisation`,
`/api/cost`).

**Sacred** : aucune modification de `cost_engine`. Le résultat
rebobinage est stocké comme ligne ADDITIVE dans `devis.payload_output`
sous la clé `"rebobinage"` ; le champ dénormalisé `ht_total_eur`
(qui reflète le résultat cost_engine pur) reste inchangé. L'UI
composera l'affichage en sommant les lignes.

Convention payload_output.rebobinage :
{
  "applique": true,
  "machine_rebobineuse_id": 1,
  "cout_total_rebobinage_eur": "...",
  "cout_mandrins_eur": "...",
  "details": { ... ResultatRebobinage sérialisé ... }
}
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import (
    Devis,
    MachineRebobineuse,
    ParametreMandrin,
    User,
)
from app.schemas.rebobinage import (
    RebobinageCalculerRequest,
    ResultatRebobinageOut,
)
from app.services.rebobinage import (
    ChoixOperateur,
    MachineRebobinageParams,
    ParametresMandrinRuntime,
    ProfilClient,
    RebobinageError,
    ResultatRebobinage,
    SpecLot,
    TarifsMandrins,
    calculer_rebobinage,
)
from app.services.scope_service import get_or_404_scoped


router = APIRouter(tags=["rebobinage"])


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


def _load_machine_or_404(
    db: Session, machine_id: int, user: User
) -> MachineRebobineuse:
    """Charge la rebobineuse + scope multi-tenant. 404 si introuvable
    pour ce tenant."""
    return get_or_404_scoped(db, MachineRebobineuse, machine_id, user)


def _load_parametres_mandrin_or_default(
    db: Session, user: User
) -> ParametresMandrinRuntime:
    """Lookup du singleton `parametre_mandrin` du tenant. Defaults
    défensifs si la row n'existe pas (cas DB sans seed migration ou
    test isolé) : `scie_disponible=False, mode="auto"` — équivalent
    à un tenant qui n'a pas encore configuré son atelier."""
    row = (
        db.query(ParametreMandrin)
        .filter_by(entreprise_id=user.entreprise_id)
        .first()
    )
    if row is None:
        return ParametresMandrinRuntime(
            scie_disponible=False, mode_par_defaut="auto"
        )
    return ParametresMandrinRuntime(
        scie_disponible=row.scie_disponible,
        mode_par_defaut=row.mode_par_defaut,  # type: ignore[arg-type]
    )


def _request_to_inputs(
    payload: RebobinageCalculerRequest,
    machine: MachineRebobineuse,
    parametres: ParametresMandrinRuntime,
) -> tuple[
    SpecLot,
    ProfilClient,
    MachineRebobinageParams,
    TarifsMandrins,
    ParametresMandrinRuntime,
    ChoixOperateur,
]:
    """Mappe le payload HTTP vers les dataclasses du moteur (Lot B)."""
    spec = SpecLot(
        nb_etiquettes_total=payload.spec_lot.nb_etiquettes_total,
        intervalle_developpe_mm=payload.spec_lot.intervalle_developpe_mm,
        epaisseur_matiere_mm=payload.spec_lot.epaisseur_matiere_mm,
    )
    profil = ProfilClient(
        diametre_mandrin_mm=payload.profil_client.diametre_mandrin_mm,
        diametre_max_bobine_mm=payload.profil_client.diametre_max_bobine_mm,
        nb_etiq_par_bobine_fixe=payload.profil_client.nb_etiq_par_bobine_fixe,
    )
    mach_params = MachineRebobinageParams(
        vitesse_pratique_m_min=machine.vitesse_pratique_m_min,
        cout_horaire_eur=Decimal(machine.cout_horaire_eur),
        temps_changement_bobine_min=Decimal(machine.temps_changement_bobine_min),
    )
    tarifs = TarifsMandrins(
        prix_pre_coupe_par_mandrin_eur=payload.tarifs_mandrins.prix_pre_coupe_par_mandrin_eur,
        cout_decoupe_interne_par_mandrin_eur=payload.tarifs_mandrins.cout_decoupe_interne_par_mandrin_eur,
        cout_fixe_decoupe_interne_eur=payload.tarifs_mandrins.cout_fixe_decoupe_interne_eur,
    )
    choix = ChoixOperateur(
        mode=payload.mode, motif_force=payload.motif_force
    )
    return spec, profil, mach_params, tarifs, parametres, choix


def _resultat_to_out(
    result: ResultatRebobinage, machine_id: int
) -> ResultatRebobinageOut:
    """Sérialise le résultat moteur vers la réponse HTTP, en ajoutant
    le snapshot id machine pour faciliter l'affichage UI."""
    return ResultatRebobinageOut(
        bobines=result.bobines,
        temps=result.temps,
        arbitrage=result.arbitrage,
        cout_mandrins_eur=result.cout_mandrins_eur,
        cout_total_rebobinage_eur=result.cout_total_rebobinage_eur,
        machine_rebobineuse_id=machine_id,
    )


def _resultat_to_payload_dict(
    result: ResultatRebobinage, machine_id: int
) -> dict[str, Any]:
    """Convertit le résultat en dict JSON-sérialisable pour stockage
    dans `devis.payload_output["rebobinage"]`. Convertit les Decimal
    en str pour préserver la précision sans dépendre de la sérialisation
    JSON Python (qui float-ifie les Decimal)."""
    return {
        "applique": True,
        "machine_rebobineuse_id": machine_id,
        "cout_mandrins_eur": str(result.cout_mandrins_eur),
        "cout_total_rebobinage_eur": str(result.cout_total_rebobinage_eur),
        "mode_applique": result.arbitrage.mode_applique,
        "mode_optimal": result.arbitrage.mode_optimal,
        "ecart_pct": str(result.arbitrage.ecart_pct),
        "motif_force": result.arbitrage.motif_force,
        "details": {
            "bobines": {
                "nb_etiq_par_bobine": result.bobines.nb_etiq_par_bobine,
                "nb_bobines": result.bobines.nb_bobines,
                "bobine_partielle": result.bobines.bobine_partielle,
                "nb_etiq_derniere_bobine": result.bobines.nb_etiq_derniere_bobine,
                "longueur_totale_m": str(result.bobines.longueur_totale_m),
            },
            "temps": {
                "temps_roulage_min": str(result.temps.temps_roulage_min),
                "temps_changements_min": str(result.temps.temps_changements_min),
                "temps_total_min": str(result.temps.temps_total_min),
                "cout_machine_eur": str(result.temps.cout_machine_eur),
            },
            "arbitrage": {
                "cout_pre_coupe_total_eur": str(
                    result.arbitrage.cout_pre_coupe_total_eur
                ),
                "cout_decoupe_interne_total_eur": str(
                    result.arbitrage.cout_decoupe_interne_total_eur
                ),
            },
        },
    }


def _executer_moteur(
    payload: RebobinageCalculerRequest, db: Session, user: User
) -> tuple[ResultatRebobinage, MachineRebobineuse]:
    """Pipeline interne partagé : lookup DB + appel moteur Lot B.

    Mappe `ValueError` → 422 et `RebobinageError` → 422 avec messages
    explicites côté API client.
    """
    machine = _load_machine_or_404(db, payload.machine_rebobineuse_id, user)
    parametres = _load_parametres_mandrin_or_default(db, user)
    inputs = _request_to_inputs(payload, machine, parametres)

    try:
        result = calculer_rebobinage(
            spec=inputs[0],
            profil_client=inputs[1],
            machine=inputs[2],
            tarifs=inputs[3],
            parametres=inputs[4],
            choix=inputs[5],
        )
    except RebobinageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Calcul rebobinage refusé : {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input rebobinage invalide : {exc}",
        ) from exc

    return result, machine


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/api/rebobinage/calculer",
    response_model=ResultatRebobinageOut,
)
def calculer_rebobinage_preview(
    payload: RebobinageCalculerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResultatRebobinageOut:
    """Calcul preview du rebobinage — aucune persistance.

    Sert au recalcul live côté UI (toggle mode auto vs forcé, ajustement
    tarifs, etc.) sans créer/modifier de devis.

    Codes erreur :
      - 404 : machine_rebobineuse_id hors scope tenant
      - 422 : input invalide / mode forcé sans motif / scie indispo
    """
    result, machine = _executer_moteur(payload, db, user)
    return _resultat_to_out(result, machine.id)


@router.post(
    "/api/devis/{devis_id}/rebobinage",
    response_model=ResultatRebobinageOut,
)
def appliquer_rebobinage_au_devis(
    devis_id: int,
    payload: RebobinageCalculerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResultatRebobinageOut:
    """Calcule + persiste la ligne rebobinage sur le devis.

    Stocke le résultat dans `devis.payload_output["rebobinage"]` (ligne
    ADDITIVE — `ht_total_eur` denorm reste inchangé, cost_engine sacré).
    Idempotent : un 2e POST remplace la ligne précédente.

    Codes erreur :
      - 404 : devis_id ou machine_rebobineuse_id hors scope tenant
      - 422 : input invalide / mode forcé sans motif / scie indispo
    """
    devis = get_or_404_scoped(db, Devis, devis_id, user)
    result, machine = _executer_moteur(payload, db, user)

    # SQLAlchemy ne flag pas un dict mutable comme "dirty". On RÉASSIGNE
    # explicitement pour déclencher l'UPDATE en DB.
    payload_output = dict(devis.payload_output) if devis.payload_output else {}
    payload_output["rebobinage"] = _resultat_to_payload_dict(result, machine.id)
    devis.payload_output = payload_output

    db.commit()
    db.refresh(devis)

    return _resultat_to_out(result, machine.id)


@router.delete(
    "/api/devis/{devis_id}/rebobinage",
    status_code=status.HTTP_204_NO_CONTENT,
)
def retirer_rebobinage_du_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Retire la ligne rebobinage du devis.

    Idempotent : 204 même si la ligne n'était pas présente. Permet à
    l'UI de revenir en arrière (toggle on/off de la ligne).
    """
    devis = get_or_404_scoped(db, Devis, devis_id, user)
    payload_output = dict(devis.payload_output) if devis.payload_output else {}
    if "rebobinage" in payload_output:
        payload_output.pop("rebobinage")
        devis.payload_output = payload_output
        db.commit()
