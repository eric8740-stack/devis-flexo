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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Client,
    Complexe,
    ConfigCouts,
    CylindreMagnetique,
    Devis,
    Entreprise,
    LotProduction,
    Machine,
)
from app.schemas.devis import DevisInput
from app.schemas.devis_persist import DevisCreate, DevisUpdate, NbCouleursIn
from app.services.cost_engine.errors import CostEngineError
from app.services.optimisation.bat_calculs import (
    calcul_laize_papier,
    calcul_laize_plaque,
)
from app.services.optimisation.sans_outil import calculer_geometrie_sans_outil
from app.services.cost_engine_aggregator import calculer_devis_multilots
from app.services.devis_total import ht_total_avec_rebobinage
from app.services.numero_devis_service import generate_next_numero

logger = logging.getLogger(__name__)

# Fix 409 (migration y9n2i3g7d5f0) — borne du retry loop autour de l'INSERT
# Devis sur collision UNIQUE(entreprise_id, numero). Couvre la race residuelle
# entre `generate_next_numero(MAX+1)` et l'INSERT effectif quand deux POST du
# meme tenant arrivent simultanement. Au-dela on relaie l'IntegrityError au
# handler global -> 409 explicite.
_MAX_RETRIES_NUMERO = 5
# Sous-chaines utilisees pour detecter une collision sur notre UNIQUE composite
# dans le message psycopg / sqlite (l'index s'appelle pareil sur les 2
# dialectes : `ix_devis_entreprise_id_numero`).
_COLLISION_HINTS = ("ix_devis_entreprise_id_numero", "devis.numero")


def _is_numero_collision(exc: IntegrityError) -> bool:
    """True si l'IntegrityError vient de notre UNIQUE(entreprise_id, numero).

    Toute autre violation (FK invalide, NOT NULL manquant) doit etre laissee
    remonter telle quelle vers le handler global -- pas de masquage.
    """
    msg = (str(exc.orig) if exc.orig is not None else str(exc)).lower()
    return any(hint in msg for hint in _COLLISION_HINTS)

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

    # P1+P2 : repoint sur Machine (parc unique). Voir migration b2c3d4e5f6g7.
    machine = db.get(Machine, lot.machine_id)
    setattr(
        lot,
        "machine_nom",
        machine.nom if machine else f"Machine #{lot.machine_id}",
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

    # Fix 409 — retry loop sur collision UNIQUE(entreprise_id, numero).
    # Cause historique : generate_next_numero etait `count+1` non scope
    # tenant -> rebouchait les trous laisses par hard-delete. Le service
    # est passe en `MAX+1 scope tenant` (migration y9n2i3g7d5f0) ; il reste
    # une race entre lecture du MAX et INSERT effectif (2 POST simultanes
    # du meme tenant). On la borne ici.
    devis: Devis | None = None
    last_exc: IntegrityError | None = None
    for _tentative in range(_MAX_RETRIES_NUMERO):
        devis = Devis(
            # S12-C : entreprise_id passe en parametre par le router (user.entreprise_id)
            entreprise_id=entreprise_id,
            numero=generate_next_numero(db, entreprise_id),
            statut=data.statut,
            client_id=data.client_id,
            payload_input=data.payload_input,
            payload_output=data.payload_output,
            cylindre_choisi_z=data.cylindre_choisi_z,
            cylindre_choisi_nb_etiq=data.cylindre_choisi_nb_etiq,
            # Sprint 14 Lot 1 — brief client unifie. Lot 1 avait cable le modele DB
            # et le schema Pydantic mais OUBLIE le CRUD : sans ces 5 lignes, les
            # valeurs envoyees par l'API etaient silencieusement remplacees par
            # les server_default DB (bug detecte par Lot 5 E2E pipeline).
            nb_etiquettes_par_rouleau=data.nb_etiquettes_par_rouleau,
            diametre_max_bobine_mm=data.diametre_max_bobine_mm,
            nb_fronts_sortie=data.nb_fronts_sortie,
            type_entree_fichier=data.type_entree_fichier,
            conditions_stockage=data.conditions_stockage,
            **denorm,
        )
        db.add(devis)
        try:
            db.flush()  # On a besoin de devis.id avant de creer les lots.
            break
        except IntegrityError as exc:
            db.rollback()
            if not _is_numero_collision(exc):
                # FK invalide, NOT NULL manquant : on laisse remonter
                # tel quel au handler global.
                raise
            last_exc = exc
            # On reboucle avec un nouveau numero. L'instance `devis`
            # courante est detached suite au rollback ; la prochaine
            # iteration la recree from scratch.
    else:
        # _MAX_RETRIES_NUMERO collisions consecutives -- tres improbable
        # en pratique. On rebascule la derniere exception au handler global.
        assert last_exc is not None
        raise last_exc

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
                # L1 — bord latéral surchargeable (NULL = défaut chute_min).
                bord_lateral_mm=lot_in.bord_lateral_mm,
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
        # Bug #5 — 1 calage par montage : signature = (cylindre, machine,
        # poses dev). `nb_poses_laize` est VOLONTAIREMENT exclu : changer la
        # laize (poses en travers) sur le même cylindre + presse = même
        # montage (mêmes clichés montés) → AUCUN nouveau calage (convention
        # métier Eric). `nb_poses_dev` reste un garde-fou : une disposition de
        # clichés AUTOUR du cylindre différente = montage réellement distinct.
        # Le vrai 2e jeu de die/clichés (même cylindre) = override
        # `changement_outil_cliche` à venir (backlog).
        montage_signatures = [
            (lot.cylindre_id, lot.machine_id, lot.nb_poses_dev)
            for lot in lots
        ]
        cout_agrege = calculer_devis_multilots(
            db, entreprise_id, devis_inputs, montage_signatures=montage_signatures
        )
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
    po = dict(devis.payload_output)
    po["mode"] = "multi-lots"
    # INVARIANT SACRÉ : prix_vente_ht_eur = base cost_engine PUR (benchmark/
    # tripwire) — jamais augmenté du rebobinage.
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

    # ht_total = base cost_engine + contribution rebobinage (multilots si
    # présent, sinon mono-lot, sinon 0). À la création, aucune ligne
    # rebobinage → ht_total = base (tripwire/benchmark inchangés). Si le devis
    # est re-chiffré APRÈS application d'un rebobinage, la ligne est préservée
    # dans `po` → le total la reflète (bug #6 6.2e-final).
    devis.ht_total_eur = ht_total_avec_rebobinage(
        cout_agrege.prix_vente_ht_total_eur, po
    )

    # Persistance cout_lot_ht_eur sur chaque LotProduction (champ existant).
    for lot, detail in zip(lots, cout_agrege.details_par_lot):
        lot.cout_lot_ht_eur = detail.prix_vente_ht_eur


def _calcul_laize_papier_lot(
    db: Session, entreprise_id: int, lot: LotProduction, format_l: int
) -> Decimal | None:
    """L1 — laize papier déterministe d'un lot (plaque + 2×bord, arrondi
    palier, plancher roulable). Plomberie pour DevisInput ; NON consommée par
    P1. GARDÉE : retourne None sur toute donnée manquante/incohérente (le
    cost_engine ignore ce champ → jamais bloquant pour le chiffrage)."""
    try:
        entreprise = db.get(Entreprise, entreprise_id)
        if entreprise is None:
            return None
        chute_min = float(entreprise.chute_laterale_min_mm)
        palier = int(entreprise.palier_laize_papier_mm)
        bord = (
            float(lot.bord_lateral_mm)
            if lot.bord_lateral_mm is not None
            else chute_min
        )
        cfg = (
            db.query(ConfigCouts)
            .filter_by(entreprise_id=entreprise_id)
            .first()
        )
        laize_mini = float(cfg.laize_mini_roulable_mm) if cfg else 0.0
        if lot.largeur_plaque_mm is not None:
            laize_plaque = float(lot.largeur_plaque_mm)
        else:
            interv = float(lot.intervalle_laize_reel_mm or 0)
            laize_plaque = calcul_laize_plaque(
                lot.nb_poses_laize, float(format_l), interv
            )
        # L2 — plafond laize_utile de la machine du lot : le bord d'échenillage
        # est rogné quand plaque + 2×bord dépasse la laize utile presse.
        machine = db.get(Machine, lot.machine_id)
        laize_utile = (
            float(machine.laize_utile_mm)
            if machine is not None and machine.laize_utile_mm is not None
            else None
        )
        papier = calcul_laize_papier(
            laize_plaque, bord, palier, laize_mini, laize_utile
        )
        return Decimal(str(papier))
    except Exception:  # noqa: BLE001 — plomberie non-bloquante (P1 ignore)
        return None


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

    # Machine d'impression (laize utile). P1+P2 : repoint sur Machine (parc
    # unique post-fusion MI -> Machine, cf migration b2c3d4e5f6g7).
    machine = db.get(Machine, lot.machine_id)
    if machine is None:
        raise ValueError(
            f"Machine ({lot.machine_id}) introuvable — FK cassée."
        )

    # Format étiquette : depuis payload_input ou defaults DevisInput.
    format_l = int(payload_input.get("format_etiquette_largeur_mm", 60))
    format_h = int(payload_input.get("format_etiquette_hauteur_mm", 40))

    # Lot back A — laize papier consommée par P1 (None par défaut → P1 retombe
    # sur la plomberie L1/L2 ci-dessous). En mode sans outil, P1 facture la
    # laize STOCK entière (déchet inclus).
    laize_papier_sans_outil: Decimal | None = None

    if lot.mode_sans_outil:
        # 2ᵉ chemin de calcul — impression pleine largeur + refente. PAS de
        # cylindre (développé libre), ml cylinder-free, intervalle_dev=0.
        laize_presse = float(
            machine.laize_utile_mm
            if machine.laize_utile_mm is not None
            else machine.laize_max_mm
        )
        laize_stock = (
            float(lot.laize_stock_mm)
            if lot.laize_stock_mm is not None
            else laize_presse
        )
        interv_laize = float(lot.intervalle_laize_reel_mm or 0)
        # Le lot porte le nb de filles CHOISI dans `nb_poses_laize` (= nb_filles
        # en sans outil) → on l'impose pour que la ml/déchet reflètent la config
        # retenue (y compris un override opérateur). 0/absent → dérivation auto.
        nb_filles_lot = (
            int(lot.nb_poses_laize)
            if lot.nb_poses_laize and lot.nb_poses_laize > 0
            else None
        )
        geo = calculer_geometrie_sans_outil(
            laize_stock_mm=laize_stock,
            laize_utile_presse_mm=laize_presse,
            format_largeur_mm=float(format_l),
            format_hauteur_mm=float(format_h),
            intervalle_laize_mm=interv_laize,
            quantite=lot.quantite,
            nb_filles_force=nb_filles_lot,
        )
        if geo is None:
            raise ValueError(
                "Lot sans outil : format plus large que la laize imprimable "
                f"(stock={laize_stock} mm, presse={laize_presse} mm)."
            )
        ml_total = max(1, int(geo.ml_total))
        # P1 facture la laize STOCK entière (déchet latéral inclus, spec V1).
        laize_papier_sans_outil = Decimal(str(laize_stock))
    else:
        # Développé du cylindre magnétique du lot (chemin standard avec outil).
        cyl = db.get(CylindreMagnetique, lot.cylindre_id)
        if cyl is None:
            raise ValueError(
                f"Cyl ({lot.cylindre_id}) introuvable — FK cassée."
            )
        nb_poses_total = lot.nb_poses_dev * lot.nb_poses_laize
        # ml_total = nombre de tours nécessaires × développé cyl. On considère
        # 1 tour = nb_poses_total étiquettes (pas d'assouplissement gâche ici,
        # le cost_engine ajoutera sa marge de roulage).
        nb_tours = math.ceil(lot.quantite / nb_poses_total)
        developpe_m = float(cyl.developpe_mm) / 1000.0
        ml_total = max(1, math.ceil(nb_tours * developpe_m))

    # Brief #33 — marge override globale du devis lue depuis payload_input
    # (étape 4 chiffrage). None = utiliser le default entreprise.
    pct_marge_raw = payload_input.get("pct_marge_override")
    pct_marge_override = (
        Decimal(str(pct_marge_raw))
        if pct_marge_raw is not None
        else None
    )

    # P1+P2 : fallback laize_utile_mm -> laize_max_mm si NULL (pattern B3a
    # deja eprouve dans optimisation_loader). Garantit qu'un nouveau tenant
    # qui n'a pas encore configure laize_utile via UI B2 utilise la
    # laize_max comme valeur par defaut raisonnable.
    laize_utile_val = (
        machine.laize_utile_mm
        if machine.laize_utile_mm is not None
        else machine.laize_max_mm
    )

    # Laize papier consommée par P1 (L2). En mode sans outil : laize STOCK
    # entière (déchet inclus). Sinon : laize papier déterministe L1/L2
    # (plaque + 2×bord, arrondi palier, plancher roulable, plafond laize utile).
    if lot.mode_sans_outil:
        laize_papier_val = laize_papier_sans_outil
    else:
        laize_papier_val = _calcul_laize_papier_lot(
            db, entreprise_id, lot, format_l
        )

    return DevisInput(
        complexe_id=complexe.id,
        laize_utile_mm=int(laize_utile_val),
        ml_total=ml_total,
        laize_papier_mm=laize_papier_val,
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
        # Lot back A — écho du mode sans outil dans le DevisInput (audit). P1
        # consomme la laize stock via `laize_papier_mm` ci-dessus. `bool(...)`
        # car un lot transient (preview, non flush) porte `None` (le
        # server_default ne s'applique qu'à l'INSERT).
        mode_sans_outil=bool(lot.mode_sans_outil),
        laize_stock_mm=lot.laize_stock_mm,
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
        # Fix regression rapport + plan : quand le serveur vient de recalculer
        # payload_output via `_chiffrer_devis_multilots`, un payload_output
        # transmis par le body (placeholder front du flux optim etape 4 par
        # exemple) ne doit PAS l'ecraser dans la boucle `setattr` ci-dessous.
        # Idem payload_input : le moteur s'appuie sur `devis.payload_input` qui
        # contient l'etat persistant ; le body ne doit pas non plus l'ecraser
        # de facon a desynchroniser le payload_output deja recalcule. Option D
        # : pop conditionnel uniquement quand un recalcul a eu lieu (lots
        # fournis). Le flux mono-config legacy (DevisSaveBar, sans lots) garde
        # son contrat actuel : le body decrit le payload stocke tel quel.
        fields.pop("payload_output", None)
        fields.pop("payload_input", None)

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

    # Fix 409 — meme retry loop que create_devis : la collision UNIQUE
    # (entreprise_id, numero) peut survenir si deux duplicate_devis du
    # meme tenant arrivent simultanement et lisent le meme MAX.
    src_entreprise_id = src.entreprise_id
    src_snapshot = {
        "client_id": src.client_id,
        "payload_input": src.payload_input,
        "payload_output": src.payload_output,
        "mode_calcul": src.mode_calcul,
        "cylindre_choisi_z": src.cylindre_choisi_z,
        "cylindre_choisi_nb_etiq": src.cylindre_choisi_nb_etiq,
        "ht_total_eur": src.ht_total_eur,
        "format_h_mm": src.format_h_mm,
        "format_l_mm": src.format_l_mm,
        "machine_id": src.machine_id,
        "nb_etiquettes_par_rouleau": src.nb_etiquettes_par_rouleau,
        "diametre_max_bobine_mm": src.diametre_max_bobine_mm,
        "nb_fronts_sortie": src.nb_fronts_sortie,
        "type_entree_fichier": src.type_entree_fichier,
        "conditions_stockage": src.conditions_stockage,
    }

    nouveau: Devis | None = None
    last_exc: IntegrityError | None = None
    for _tentative in range(_MAX_RETRIES_NUMERO):
        nouveau = Devis(
            # S12-A : copie l'entreprise_id du devis source (preserve le scope tenant)
            entreprise_id=src_entreprise_id,
            numero=generate_next_numero(db, src_entreprise_id),
            statut="brouillon",
            **src_snapshot,
        )
        db.add(nouveau)
        try:
            db.flush()
            break
        except IntegrityError as exc:
            db.rollback()
            if not _is_numero_collision(exc):
                raise
            last_exc = exc
    else:
        assert last_exc is not None
        raise last_exc

    db.commit()
    db.refresh(nouveau)
    return _attach_relation_names(nouveau, db)
