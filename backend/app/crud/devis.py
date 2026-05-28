"""CRUD Devis (Sprint 4 Lot 4b) — persistance + dénormalisation auto.

Lors d'un POST, on extrait du payload_input/payload_output les champs
dénormalisés (mode, format, machine_id, ht_total) pour permettre à la
liste paginée d'éviter le parsing JSON ligne par ligne.

Lors d'un duplicate, on copie le devis source en forçant statut='brouillon'
et en générant un nouveau numéro via numero_devis_service.
"""
import logging
import math
from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    Client,
    Complexe,
    CylindreMagnetique,
    Devis,
    LotProduction,
    Machine,
    MachineImprimerie,
)
from app.schemas.devis import DevisInput
from app.schemas.devis_persist import DevisCreate, DevisUpdate, NbCouleursIn
from app.services.cost_engine.errors import CostEngineError
from app.services.cost_engine_aggregator import calculer_devis_multilots
from app.services.numero_devis_service import generate_next_numero

logger = logging.getLogger(__name__)

# Sprint 16 fix chiffrage — message métier affiché quand le chiffrage auto
# d'un devis multi-lots optim échoue (cause connue : matière du lot non
# reliée à un complexe de coût — les catalogues `matiere` (optim) et
# `complexe` (cost_engine) ne sont pas encore pontés). Option B : devis
# créé en "chiffrage incomplet" (ht_total_eur NULL), jamais un 0 € trompeur.
MSG_CHIFFRAGE_INDISPONIBLE = (
    "Matière du lot non reliée à un complexe de coût — chiffrage auto "
    "indisponible, devis à finaliser manuellement."
)


def _mapper_nb_couleurs(nb_couleurs: NbCouleursIn | None) -> dict[str, int]:
    """Sprint 16 fix chiffrage — mappe les compteurs couleurs du payload
    vers `nb_couleurs_par_type` (clés = `tarif_encre.type_encre` réels).

    Clés cibles vérifiées dans seeds/tarif_encre.csv :
      process_cmj | process_black_hc | pantone | blanc_high_opaque | metallise.

    Mapping retenu :
      - impression → "process_cmj"        (couleurs process quadri)
      - pantone    → "pantone"
      - blanc      → "blanc_high_opaque"
      - vernis     → NON mappé : le vernis est une finition (Poste 6),
                     pas une encre (Poste 2). Inclure une clé inexistante
                     ferait lever CostEngineError côté moteur.

    Seuls les compteurs > 0 sont inclus (le moteur P2 ignore déjà les 0,
    mais on garde le dict minimal). None ou tout-à-zéro → {} (P2 = 0 €,
    comportement antérieur préservé pour les payloads sans couleurs).
    """
    if nb_couleurs is None:
        return {}
    result: dict[str, int] = {}
    if nb_couleurs.impression > 0:
        result["process_cmj"] = nb_couleurs.impression
    if nb_couleurs.pantone > 0:
        result["pantone"] = nb_couleurs.pantone
    if nb_couleurs.blanc > 0:
        result["blanc_high_opaque"] = nb_couleurs.blanc
    return result


# ---------------------------------------------------------------------------
# Extraction des dénormalisés depuis payload_input / payload_output
# ---------------------------------------------------------------------------


def _extract_denormalised_fields(
    payload_input: dict, payload_output: dict
) -> dict:
    """Lit les champs nécessaires à la liste paginée depuis les payloads.

    Sources :
      mode_calcul, machine_id, format_h_mm, format_l_mm : payload_input
      ht_total_eur : payload_output (manuel direct, matching = 1er candidat
                     car HT identique entre candidats — postes ne dépendent
                     pas du cylindre dans le moteur Sprint 7 V2)
    """
    mode = payload_input.get("mode_calcul", "manuel")
    machine_id = payload_input["machine_id"]
    format_h = Decimal(str(payload_input["format_etiquette_hauteur_mm"]))
    format_l = Decimal(str(payload_input["format_etiquette_largeur_mm"]))

    if mode == "matching":
        candidats = payload_output.get("candidats") or []
        if not candidats:
            raise ValueError(
                "payload_output mode 'matching' doit contenir au moins 1 candidat"
            )
        ht = Decimal(str(candidats[0]["prix_vente_ht_eur"]))
    else:
        ht = Decimal(str(payload_output["prix_vente_ht_eur"]))

    return {
        "mode_calcul": mode,
        "machine_id": machine_id,
        "format_h_mm": format_h,
        "format_l_mm": format_l,
        "ht_total_eur": ht,
    }


# ---------------------------------------------------------------------------
# Helpers d'enrichissement (client_nom + machine_nom) pour les schémas Read
# ---------------------------------------------------------------------------


def _attach_relation_names(devis: Devis, db: Session) -> Devis:
    """Pose des attributs dynamiques `client_nom` / `machine_nom` sur le
    Devis avant sérialisation Pydantic from_attributes.

    Brief #32 commit 3 : enrichit aussi chaque lot_production avec ses
    joints (machine_nom, cylindre_nb_dents, matiere_libelle,
    sens_enroulement_libelle, rotation_vue_a/c_deg) pour permettre
    `DevisResultMultiLots` côté UI sans N+1.
    """
    machine = db.get(Machine, devis.machine_id)
    setattr(devis, "machine_nom", machine.nom if machine else "")
    if devis.client_id is not None:
        client = db.get(Client, devis.client_id)
        setattr(
            devis,
            "client_nom",
            client.raison_sociale if client else None,
        )
    else:
        setattr(devis, "client_nom", None)

    # Brief #32 — enrichissement des lots avec joints UI.
    for lot in devis.lots_production:
        _enrichir_lot_pour_read(lot, db)
    return devis


def _enrichir_lot_pour_read(lot: LotProduction, db: Session) -> None:
    """Pose les attributs dynamiques sur le lot avant sérialisation
    Pydantic (jointures machine/cylindre/matière + rotation_se).
    """
    # Imports locaux pour éviter import circulaire au chargement du module.
    from app.models import Matiere
    from app.services.sens_metadata import (
        get_libelle_officiel,
        get_rotation_vue_a,
        get_rotation_vue_c,
    )

    machine_imp = db.get(MachineImprimerie, lot.machine_id)
    setattr(
        lot,
        "machine_nom",
        machine_imp.nom if machine_imp else f"Machine #{lot.machine_id}",
    )
    cyl = db.get(CylindreMagnetique, lot.cylindre_id)
    if cyl is not None:
        setattr(lot, "cylindre_developpe_mm", cyl.developpe_mm)
        # 1 dent = 3.175 mm (DENTS_TO_MM_FACTOR catalogue_defaults).
        setattr(
            lot,
            "cylindre_nb_dents",
            int(round(float(cyl.developpe_mm) / 3.175)),
        )
    else:
        setattr(lot, "cylindre_developpe_mm", None)
        setattr(lot, "cylindre_nb_dents", None)
    mat = db.get(Matiere, lot.matiere_id)
    setattr(lot, "matiere_libelle", mat.libelle if mat else None)
    # Métadonnées sens : façade sens_metadata (1-8 délégués à rotation_se
    # verrouillé, 0/9 = bobines vierges sans impression gérées localement).
    sens = lot.sens_enroulement if 0 <= lot.sens_enroulement <= 9 else 1
    setattr(lot, "sens_enroulement_libelle", get_libelle_officiel(sens))
    setattr(lot, "rotation_vue_a_deg", get_rotation_vue_a(sens))
    setattr(lot, "rotation_vue_c_deg", get_rotation_vue_c(sens))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


SORT_MAP = {
    "date_desc": Devis.date_creation.desc(),
    "date_asc": Devis.date_creation.asc(),
    "numero_asc": Devis.numero.asc(),
    "ht_desc": Devis.ht_total_eur.desc(),
}


def list_devis(
    db: Session,
    entreprise_id: int,
    page: int = 1,
    per_page: int = 25,
    search: str | None = None,
    statut: str | None = None,
    sort: str = "date_desc",
) -> tuple[list[Devis], int]:
    """Liste paginée + tri + recherche scopée par entreprise (S12-C).

    Retourne (items_de_la_page, total_count).
    """
    query = (
        db.query(Devis)
        .outerjoin(Client, Devis.client_id == Client.id)
        .filter(Devis.entreprise_id == entreprise_id)
    )

    if statut:
        query = query.filter(Devis.statut == statut)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Devis.numero.ilike(like), Client.raison_sociale.ilike(like))
        )

    total = query.count()
    order_by = SORT_MAP.get(sort, SORT_MAP["date_desc"])
    items = (
        query.order_by(order_by)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    for d in items:
        _attach_relation_names(d, db)
    return items, total


def get_devis(db: Session, devis_id: int) -> Devis | None:
    devis = db.get(Devis, devis_id)
    if devis is None:
        return None
    return _attach_relation_names(devis, db)


def create_devis(
    db: Session, data: DevisCreate, entreprise_id: int
) -> Devis:
    """Crée un devis : génère numero auto + extrait dénormalisés.

    S12-C : `entreprise_id` injecté par le router via user.entreprise_id.

    Sprint 13 avenant : si `data.lots` est fourni, crée N LotProduction
    rattachés au devis (ordre 1..N). La validation `Σ qté == quantite_totale`
    est déjà faite par le validator Pydantic de DevisCreate.

    Brief #32 commit 1 : pour les devis multi-lots, chiffrage automatique
    via cost_engine_aggregator. Le payload_output minimal envoyé par le
    workflow optim (placeholder prix=0) est ÉCRASÉ par le résultat du
    cost_engine — devis sort avec prix réel + détail par lot. Si la
    reconstruction des DevisInput échoue (champs manquants, complexe
    introuvable), fallback gracieux : devis créé avec prix=0 + note
    "chiffrage à compléter via /devis/[id]/edit".
    """
    denorm = _extract_denormalised_fields(data.payload_input, data.payload_output)
    numero = generate_next_numero(db)
    devis = Devis(
        # S12-C : entreprise_id passé en paramètre par le router (user.entreprise_id)
        entreprise_id=entreprise_id,
        numero=numero,
        statut=data.statut,
        client_id=data.client_id,
        payload_input=data.payload_input,
        payload_output=data.payload_output,
        cylindre_choisi_z=data.cylindre_choisi_z,
        cylindre_choisi_nb_etiq=data.cylindre_choisi_nb_etiq,
        # Sprint 14 Lot 1 — brief client unifié. Lot 1 avait câblé le modèle DB
        # et le schema Pydantic mais OUBLIÉ le CRUD : sans ces 5 lignes, les
        # valeurs envoyées par l'API étaient silencieusement remplacées par
        # les server_default DB (bug détecté par Lot 5 E2E pipeline).
        nb_etiquettes_par_rouleau=data.nb_etiquettes_par_rouleau,
        diametre_max_bobine_mm=data.diametre_max_bobine_mm,
        nb_fronts_sortie=data.nb_fronts_sortie,
        type_entree_fichier=data.type_entree_fichier,
        conditions_stockage=data.conditions_stockage,
        **denorm,
    )
    db.add(devis)
    db.flush()  # On a besoin de devis.id avant de créer les lots.

    # Sprint 13 avenant — lots de production (cascade depuis devis.id).
    lots_persistes: list[LotProduction] = []
    if data.lots:
        for ordre, lot_in in enumerate(data.lots, start=1):
            lot = LotProduction(
                devis_id=devis.id,
                entreprise_id=entreprise_id,
                ordre=ordre,
                cylindre_id=lot_in.cylindre_id,
                machine_id=lot_in.machine_id,
                nb_poses_dev=lot_in.nb_poses_dev,
                nb_poses_laize=lot_in.nb_poses_laize,
                sens_enroulement=lot_in.sens_enroulement,
                quantite=lot_in.quantite,
                matiere_id=lot_in.matiere_id,
                intervalle_dev_reel_mm=lot_in.intervalle_dev_reel_mm,
                intervalle_laize_reel_mm=lot_in.intervalle_laize_reel_mm,
                largeur_plaque_mm=lot_in.largeur_plaque_mm,
                score_optim=lot_in.score_optim,
                cout_lot_ht_eur=lot_in.cout_lot_ht_eur,
                payload_visuel=lot_in.payload_visuel,
            )
            db.add(lot)
            lots_persistes.append(lot)

        db.flush()  # lots ont leurs ids

        # Brief #32 commit 1 — chiffrage cost_engine automatique.
        # Sprint 16 fix : propage les compteurs couleurs (Poste 2 Encres).
        _chiffrer_devis_multilots(
            db,
            devis,
            lots_persistes,
            data.payload_input,
            entreprise_id,
            _mapper_nb_couleurs(data.nb_couleurs),
        )

    db.commit()
    db.refresh(devis)
    return _attach_relation_names(devis, db)


def preview_couts_multilots(
    db: Session,
    entreprise_id: int,
    lots_data: list[dict[str, Any]],
    payload_input: dict[str, Any],
    reduction_pct: Decimal,
    nb_couleurs_par_type: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Brief #33 commit 1 — preview live des coûts sans persister.

    Reconstruit des LotProduction transitoires (sans db.add), construit
    les DevisInputs via le helper existant, appelle l'aggregator et
    applique la réduction commerciale. Retourne brut/net pour live update
    de l'étape 4 chiffrage.

    En cas d'échec (validation Pydantic, complexe manquant), retourne un
    payload avec `chiffrage_auto_erreur` non null et montants à None —
    nom de champ unifié avec la réponse POST /devis (CC2 consomme ce nom
    exact pour le bandeau "chiffrage indisponible").
    """
    # Construit des LotProduction transitoires (non persistés) pour
    # réutiliser `_construire_devis_input_pour_lot()` qui les attend.
    lots_transitoires: list[LotProduction] = [
        LotProduction(
            entreprise_id=entreprise_id,
            ordre=idx + 1,
            cylindre_id=ld["cylindre_id"],
            machine_id=ld["machine_id"],
            nb_poses_dev=ld["nb_poses_dev"],
            nb_poses_laize=ld["nb_poses_laize"],
            sens_enroulement=ld["sens_enroulement"],
            quantite=ld["quantite"],
            matiere_id=ld["matiere_id"],
        )
        for idx, ld in enumerate(lots_data)
    ]

    try:
        devis_inputs = [
            _construire_devis_input_pour_lot(
                lot, payload_input, db, entreprise_id, nb_couleurs_par_type
            )
            for lot in lots_transitoires
        ]
        cout_agrege = calculer_devis_multilots(db, entreprise_id, devis_inputs)
        cout_brut = cout_agrege.prix_vente_ht_total_eur
        chiffrage_auto_erreur = None
    except (CostEngineError, ValueError) as exc:
        # Échec MÉTIER attendu : pas de 0 € trompeur. Montants à None +
        # erreur explicite — l'UI affiche le mode "chiffrage indisponible".
        logger.warning("preview_couts_multilots indisponible : %s", exc)
        cout_brut = None
        chiffrage_auto_erreur = MSG_CHIFFRAGE_INDISPONIBLE
    # Toute autre exception (bug inattendu) n'est PAS masquée : elle remonte.

    if cout_brut is None:
        return {
            "cout_brut_ht_eur": None,
            "reduction_pct": reduction_pct,
            "reduction_eur": None,
            "cout_net_ht_eur": None,
            "nb_lots": len(lots_data),
            "chiffrage_auto_erreur": chiffrage_auto_erreur,
        }

    reduction_eur = (cout_brut * reduction_pct / Decimal(100)).quantize(
        Decimal("0.01")
    )
    cout_net = (cout_brut - reduction_eur).quantize(Decimal("0.01"))

    return {
        "cout_brut_ht_eur": cout_brut,
        "reduction_pct": reduction_pct,
        "reduction_eur": reduction_eur,
        "cout_net_ht_eur": cout_net,
        "nb_lots": len(lots_data),
        "chiffrage_auto_erreur": chiffrage_auto_erreur,
    }


def _chiffrer_devis_multilots(
    db: Session,
    devis: Devis,
    lots: list[LotProduction],
    payload_input: dict[str, Any],
    entreprise_id: int,
    nb_couleurs_par_type: dict[str, int] | None = None,
) -> None:
    """Brief #32 commit 1 — chiffrage automatique d'un devis multi-lots
    via cost_engine_aggregator.

    Construit un DevisInput "best effort" par lot avec defaults métier
    (1er complexe/machine legacy du tenant si non fournis) et appelle
    l'aggregator. En cas d'échec (validation Pydantic, exception cost
    engine), fallback gracieux : on ne casse PAS la création du devis
    — on laisse le payload_output minimal initial + on log un warning.
    L'utilisateur pourra finaliser le chiffrage via /devis/[id]/edit.

    SACRED : aucune modification de la logique cost_engine. L'aggregator
    appelle MoteurDevis N fois (1 fois par lot) sans toucher au calcul.
    """
    try:
        devis_inputs = [
            _construire_devis_input_pour_lot(
                lot, payload_input, db, entreprise_id, nb_couleurs_par_type
            )
            for lot in lots
        ]
        cout_agrege = calculer_devis_multilots(db, entreprise_id, devis_inputs)
    except (CostEngineError, ValueError) as exc:
        # Échec MÉTIER attendu (matière non reliée à un complexe, complexe
        # sans grammage, onboarding incomplet...). Option B : on NE met PAS
        # un 0 € trompeur — on laisse ht_total_eur à NULL et on remonte une
        # erreur explicite. Le devis EST créé (HTTP 201), à finaliser à la main.
        logger.warning(
            "Chiffrage automatique multi-lots indisponible pour devis %s : %s. "
            "Devis créé en chiffrage incomplet (ht_total_eur NULL).",
            devis.numero,
            exc,
        )
        devis.ht_total_eur = None
        po = dict(devis.payload_output)
        po["chiffrage_auto_erreur"] = MSG_CHIFFRAGE_INDISPONIBLE
        po["chiffrage_auto_detail"] = str(exc)
        po["note"] = (
            "Chiffrage indisponible automatiquement — finalise via "
            "Modifier ce devis."
        )
        devis.payload_output = po
        return
    # Toute autre exception (bug inattendu) n'est PAS masquée : elle remonte
    # et produit un 500 — on ne veut pas avaler silencieusement un défaut.

    # Mise à jour des résultats côté Devis + LotProduction.
    devis.ht_total_eur = cout_agrege.prix_vente_ht_total_eur
    po = dict(devis.payload_output)
    po["mode"] = "multi-lots"
    po["prix_vente_ht_eur"] = str(cout_agrege.prix_vente_ht_total_eur)
    po["cout_revient_total_eur"] = str(cout_agrege.cout_revient_total_eur)
    po["nb_lots"] = cout_agrege.nb_lots
    po["details_par_lot"] = [
        {
            "ordre": detail.ordre,
            "prix_vente_ht_eur": str(detail.prix_vente_ht_eur),
            "cout_revient_eur": str(detail.cout_revient_eur),
            "details": detail.details,
        }
        for detail in cout_agrege.details_par_lot
    ]
    po["note"] = "Devis créé depuis optimisation multi-lots, chiffrage automatique."
    devis.payload_output = po

    # Persistance cout_lot_ht_eur sur chaque LotProduction (champ existant).
    for lot, detail in zip(lots, cout_agrege.details_par_lot):
        lot.cout_lot_ht_eur = detail.prix_vente_ht_eur


def _construire_devis_input_pour_lot(
    lot: LotProduction,
    payload_input: dict[str, Any],
    db: Session,
    entreprise_id: int,
    nb_couleurs_par_type: dict[str, int] | None = None,
) -> DevisInput:
    """Reconstruit un DevisInput valide pour cost_engine à partir d'un
    LotProduction + le contexte saisie (payload_input).

    Stratégie 'best effort' :
    - `complexe_id` : 1er complexe actif du tenant (le payload_input
      du workflow optim ne le porte pas ; un brief futur pourra mapper
      `lot.matiere_id` → complexe approprié pour plus de précision).
    - `machine_id` (Machine legacy, cost_engine) : 1ère Machine legacy
      active du tenant. Distincte de `lot.machine_id` qui pointe vers
      `machine_imprimerie` (modèle optim Sprint 13).
    - `laize_utile_mm` : depuis lot.machine (machine_imprimerie).
    - `ml_total` : calculé depuis quantite + poses + développé cylindre.
    - format_etiquette_* : depuis payload_input (saisie étape 1).
    - nb_poses_largeur/developpement : depuis lot.
    - nb_couleurs_par_type : {} (default — cost_engine tolère vide).

    Raise ValueError si données minimales indisponibles (no complexe, etc.).
    """
    complexe = (
        db.query(Complexe)
        .filter_by(entreprise_id=entreprise_id)
        .order_by(Complexe.id)
        .first()
    )
    if complexe is None:
        raise ValueError(
            f"Aucun complexe actif pour entreprise_id={entreprise_id}. "
            "Onboarding incomplet — impossible de chiffrer."
        )

    machine_legacy = (
        db.query(Machine)
        .filter_by(entreprise_id=entreprise_id)
        .order_by(Machine.id)
        .first()
    )
    if machine_legacy is None:
        raise ValueError(
            f"Aucune machine legacy pour entreprise_id={entreprise_id}."
        )

    # Données depuis le cylindre magnétique du lot (développé) + machine
    # d'impression (laize utile) — modèles Sprint 13.
    cyl = db.get(CylindreMagnetique, lot.cylindre_id)
    machine_imp = db.get(MachineImprimerie, lot.machine_id)
    if cyl is None or machine_imp is None:
        raise ValueError(
            f"Cyl ({lot.cylindre_id}) ou machine imprimerie ({lot.machine_id}) "
            "introuvable — FK cassée."
        )

    nb_poses_total = lot.nb_poses_dev * lot.nb_poses_laize
    # ml_total = nombre de tours nécessaires × développé cyl. On considère
    # 1 tour = nb_poses_total étiquettes (pas d'assouplissement gâche ici,
    # le cost_engine ajoutera sa marge de roulage).
    nb_tours = math.ceil(lot.quantite / nb_poses_total)
    developpe_m = float(cyl.developpe_mm) / 1000.0
    ml_total = max(1, math.ceil(nb_tours * developpe_m))

    # Format étiquette : depuis payload_input ou defaults DevisInput.
    format_l = int(payload_input.get("format_etiquette_largeur_mm", 60))
    format_h = int(payload_input.get("format_etiquette_hauteur_mm", 40))

    # Brief #33 — marge override globale du devis lue depuis payload_input
    # (étape 4 chiffrage). None = utiliser le default entreprise.
    pct_marge_raw = payload_input.get("pct_marge_override")
    pct_marge_override = (
        Decimal(str(pct_marge_raw))
        if pct_marge_raw is not None
        else None
    )

    return DevisInput(
        complexe_id=complexe.id,
        laize_utile_mm=int(machine_imp.laize_utile_mm or 320),
        ml_total=ml_total,
        # Sprint 16 fix chiffrage : nb_couleurs propagé depuis le payload
        # (mappé en amont). {} si non fourni → P2 Encres = 0 (antérieur).
        nb_couleurs_par_type=nb_couleurs_par_type or {},
        machine_id=machine_legacy.id,
        format_etiquette_largeur_mm=format_l,
        format_etiquette_hauteur_mm=format_h,
        nb_poses_largeur=lot.nb_poses_laize,
        nb_poses_developpement=lot.nb_poses_dev,
        forme_speciale=False,
        mode_calcul="manuel",
        pct_marge_override=pct_marge_override,
    )


def update_devis(
    db: Session, devis_id: int, data: DevisUpdate
) -> Devis | None:
    """Update partiel d'un devis (PUT /api/devis/{id} avec exclude_unset).

    Brief #32 commit 2 :
    - Support `reduction_pct` (0..100 %) — appliquée par-dessus
      payload_output.prix_vente_ht_eur (brut), pas de mutation du brut.
    - Support `lots` éditables : si `lots` fourni, remplace TOUS les lots
      existants (delete cascade) + insert news + recalcul cost_engine
      via aggregator (cf POST flow).
    """
    devis = db.get(Devis, devis_id)
    if devis is None:
        return None
    fields = data.model_dump(exclude_unset=True)

    # Brief #32 — lots éditables. Si fourni, replace + recalcul cost_engine.
    lots_in = fields.pop("lots", None)
    quantite_totale_in = fields.pop("quantite_totale", None)
    if lots_in is not None:
        # Validation cohérence somme (déjà partiellement faite côté Pydantic
        # DevisCreate mais DevisUpdate accepte les 2 séparément).
        if quantite_totale_in is None:
            raise ValueError(
                "Multi-lots update : quantite_totale obligatoire quand lots fourni."
            )
        somme = sum(lot["quantite"] for lot in lots_in)
        if somme != quantite_totale_in:
            raise ValueError(
                f"Multi-lots update : Σ quantités ({somme}) != totale "
                f"({quantite_totale_in})."
            )
        # Replace lots (cascade=all,delete-orphan supprime les anciens
        # automatiquement à la commit).
        for ancien in list(devis.lots_production):
            db.delete(ancien)
        db.flush()
        nouveaux_lots: list[LotProduction] = []
        for ordre, lot_dict in enumerate(lots_in, start=1):
            lot = LotProduction(
                devis_id=devis.id,
                entreprise_id=devis.entreprise_id,
                ordre=ordre,
                cylindre_id=lot_dict["cylindre_id"],
                machine_id=lot_dict["machine_id"],
                nb_poses_dev=lot_dict["nb_poses_dev"],
                nb_poses_laize=lot_dict["nb_poses_laize"],
                sens_enroulement=lot_dict["sens_enroulement"],
                quantite=lot_dict["quantite"],
                matiere_id=lot_dict["matiere_id"],
                intervalle_dev_reel_mm=lot_dict.get("intervalle_dev_reel_mm"),
                intervalle_laize_reel_mm=lot_dict.get("intervalle_laize_reel_mm"),
                largeur_plaque_mm=lot_dict.get("largeur_plaque_mm"),
                score_optim=lot_dict.get("score_optim"),
                cout_lot_ht_eur=lot_dict.get("cout_lot_ht_eur"),
                payload_visuel=lot_dict.get("payload_visuel"),
            )
            db.add(lot)
            nouveaux_lots.append(lot)
        db.flush()
        # Recalcul cost_engine_aggregator avec les nouveaux lots.
        _chiffrer_devis_multilots(
            db, devis, nouveaux_lots, devis.payload_input, devis.entreprise_id
        )

    # Si payload_input ou payload_output changent, on re-dérive dénormalisés.
    if "payload_input" in fields or "payload_output" in fields:
        new_input = fields.get("payload_input", devis.payload_input)
        new_output = fields.get("payload_output", devis.payload_output)
        denorm = _extract_denormalised_fields(new_input, new_output)
        fields.update(denorm)

    for field, value in fields.items():
        setattr(devis, field, value)
    db.commit()
    db.refresh(devis)
    return _attach_relation_names(devis, db)


def delete_devis(db: Session, devis_id: int) -> bool:
    devis = db.get(Devis, devis_id)
    if devis is None:
        return False
    db.delete(devis)
    db.commit()
    return True


def duplicate_devis(db: Session, devis_id: int) -> Devis | None:
    """Crée un nouveau devis à partir d'un existant.

    - Nouveau numéro
    - Statut forcé à 'brouillon'
    - payload_input / payload_output / client_id / cylindre / dénormalisés
      copiés
    """
    src = db.get(Devis, devis_id)
    if src is None:
        return None
    numero = generate_next_numero(db)
    nouveau = Devis(
        # S12-A : copie l'entreprise_id du devis source (préserve le scope tenant)
        entreprise_id=src.entreprise_id,
        numero=numero,
        statut="brouillon",
        client_id=src.client_id,
        payload_input=src.payload_input,
        payload_output=src.payload_output,
        mode_calcul=src.mode_calcul,
        cylindre_choisi_z=src.cylindre_choisi_z,
        cylindre_choisi_nb_etiq=src.cylindre_choisi_nb_etiq,
        ht_total_eur=src.ht_total_eur,
        format_h_mm=src.format_h_mm,
        format_l_mm=src.format_l_mm,
        machine_id=src.machine_id,
        # Sprint 14 Lot 1 — copie du brief client (cohérence avec create_devis).
        nb_etiquettes_par_rouleau=src.nb_etiquettes_par_rouleau,
        diametre_max_bobine_mm=src.diametre_max_bobine_mm,
        nb_fronts_sortie=src.nb_fronts_sortie,
        type_entree_fichier=src.type_entree_fichier,
        conditions_stockage=src.conditions_stockage,
    )
    db.add(nouveau)
    db.commit()
    db.refresh(nouveau)
    return _attach_relation_names(nouveau, db)
