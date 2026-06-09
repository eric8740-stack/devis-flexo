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
    OptionFabrication,
)
from app.schemas.devis import DevisInput, PartenaireSTForfait
from app.schemas.devis_persist import DevisCreate, DevisUpdate, NbCouleursIn
from app.services.cost_engine.errors import CostEngineError
from app.services.optimisation.bat_calculs import (
    calcul_diametre_bobine,
    calcul_laize_papier,
    calcul_laize_plaque,
)
from app.services.optimisation.sans_outil import calculer_geometrie_sans_outil
from app.services.cost_engine import MoteurDevis
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
    # Lot back A/B — cylindre_id NULL en mode sans outil (pas d'outil) : on
    # évite `db.get(..., None)` (SAWarning « fully NULL primary key »).
    cyl = (
        db.get(CylindreMagnetique, lot.cylindre_id)
        if lot.cylindre_id is not None
        else None
    )
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
                # Lot back A/B — persistance du mode sans outil (flag + laize
                # stock + override nb filles de refente).
                mode_sans_outil=lot_in.mode_sans_outil,
                laize_stock_mm=lot_in.laize_stock_mm,
                nb_filles_force=lot_in.nb_filles_force,
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


def _catalogue_options(
    db: Session, entreprise_id: int
) -> dict[str, OptionFabrication]:
    """Options actives du tenant + catalogue global, mergées par code (tenant
    prioritaire) — MÊME logique que GET /api/optimisation/options-disponibles.
    Source unique de coût : le front n'a que les codes."""
    rows = (
        db.query(OptionFabrication)
        .filter(OptionFabrication.actif.is_(True))
        .filter(
            (OptionFabrication.entreprise_id == entreprise_id)
            | (OptionFabrication.entreprise_id.is_(None))
        )
        .all()
    )
    by_code: dict[str, OptionFabrication] = {}
    for r in rows:
        ex = by_code.get(r.code)
        if ex is None or (ex.entreprise_id is None and r.entreprise_id is not None):
            by_code[r.code] = r
    return by_code


def _option_cout_eur(
    opt: OptionFabrication, surface_m2: Decimal, quantite: int
) -> tuple[Decimal | None, bool]:
    """Coût € d'une option depuis `OptionFabrication` (3 modes cumulables :
    forfait + m²×surface + mille×milliers + consommable). Retourne
    `(€ ou None, impact_production)`.

    `€ is None` + `impact_production=True` : option à impact PRODUCTION (coef
    vitesse/gâche / temps calage) sans tarif € → non chiffrée en V1 (le
    cost_engine ne price pas ces impacts). Le caller renvoie un flag, jamais
    un faux « +0 € »."""
    total = Decimal("0")
    has_price = False
    if opt.forfait_eur is not None:
        total += Decimal(str(opt.forfait_eur))
        has_price = True
    if opt.prix_au_m2_eur is not None:
        total += Decimal(str(opt.prix_au_m2_eur)) * surface_m2
        has_price = True
    if opt.prix_au_mille_eur is not None:
        total += Decimal(str(opt.prix_au_mille_eur)) * (
            Decimal(quantite) / Decimal(1000)
        )
        has_price = True
    if opt.cout_consommable_eur is not None:
        total += Decimal(str(opt.cout_consommable_eur))
        has_price = True
    if has_price:
        return total.quantize(Decimal("0.01")), False
    impact = (
        Decimal(str(opt.coef_vitesse_impact)) != Decimal("1")
        or Decimal(str(opt.coef_gache_impact)) != Decimal("1")
        or int(opt.ajoute_temps_calage_min or 0) > 0
        or int(opt.ajoute_cliches or 0) > 0
        or int(opt.ajoute_couleurs or 0) > 0
    )
    return None, impact


def _appliquer_remise(
    prix_ht_brut: Decimal, remise_pct: Decimal
) -> tuple[Decimal, Decimal]:
    """V0 — remise commerciale appliquée PAR-DESSUS le HT brut. N'affecte PAS le
    coût de revient (juste le HT facturé). Retourne `(remise_eur, prix_ht_net)`.

    Archi ouverte (sens-cible plus tard) : la MARGE reste calculée par le
    cost_engine (param `ConfigCouts.marge_standard_pct` ou override) ; la remise
    est isolée ici. Un futur mode « marge cible % / prix cible → room » s'insérera
    à ce point SANS refondre le flux `input → prix`. Pas de mode cible en V0.
    """
    remise_eur = (prix_ht_brut * remise_pct / Decimal(100)).quantize(
        Decimal("0.01")
    )
    return remise_eur, (prix_ht_brut - remise_eur).quantize(Decimal("0.01"))


# Lot C — défauts écarts (cf. brief). Intervalle laize 5 mm ; intervalle dev
# plancher imprimeur ; sens recommandé par défaut SE1 (rotation_se reste SSOT).
_ECART_INTERVALLE_LAIZE_MM = 5.0
_ECART_INTERVALLE_DEV_MIN_MM = 2.0
_CONFIG_SENS_DEFAUT = 1
_CONFIG_TOP_RECOMMANDE = 3


def _configs_preview(
    db: Session, entreprise_id: int, p: dict[str, Any]
) -> tuple[list[dict], dict | None]:
    """Lot C — configurations cylindre × machine + écarts entre étiquettes.

    RÉUTILISE le moteur `optimiser_pose` (SSOT) — géométrie/lecture PURE, AUCUN
    coût. Best-effort : `([], None)` si géométrie incomplète (laize/dev absents)
    ou parc/barèmes indisponibles. `mode_sans_outil` : pas de cylindre → pas de
    configs ; `intervalle_dev=0` (impression continue), intervalle laize conservé.
    """
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
    )

    laize = p.get("laize")
    dev = p.get("dev")
    if not laize or not dev:
        return [], None

    if bool(p.get("mode_sans_outil")):
        return [], {
            "intervalle_laize_mm": _ECART_INTERVALLE_LAIZE_MM,
            "intervalle_dev_mm": 0.0,
            "nb_poses_laize": "auto",
            "force_intervalle_laize": False,
        }

    try:
        cylindres = charger_cylindres_actifs(db, entreprise_id)
        machines = charger_machines_actives(db, entreprise_id)
        baremes = charger_baremes(db, entreprise_id)
        if not cylindres or not machines:
            return [], None
        nb_coul = 0
        if p.get("nb_couleurs"):
            nb_coul = sum(int(v or 0) for v in p["nb_couleurs"].values())
        inp = OptimisationInput(
            format=Format(hauteur_mm=float(dev), largeur_mm=float(laize)),
            intervalle_dev_min_mm=_ECART_INTERVALLE_DEV_MIN_MM,
            nb_couleurs_impression=nb_coul,
            quantite=int(p.get("quantite") or 1),
            options=[],
            cylindres=cylindres,
            machines=machines,
            bareme_echenillage=baremes["echenillage"],
            bareme_effet_banane=baremes["effet_banane"],
            bareme_compensation=baremes["compensation_laize_dev"],
            bareme_confort_roulage=baremes["confort_roulage"],
            contrainte_client=ContrainteClient(intervalle_dev_min_mm=0.0),
        )
        out = optimiser_pose(inp)
        dev_par_cyl = {c.id: c.developpe_mm for c in cylindres}
        nom_par_mach = {m.id: m.nom for m in machines}
        configs: list[dict] = []
        for i, c in enumerate(out.configurations):
            developpe = float(dev_par_cyl.get(c.cylindre_id, 0.0))
            configs.append(
                {
                    "id": (
                        f"{c.cylindre_id}-{c.machine_id}"
                        f"-{c.nb_poses_dev}x{c.nb_poses_laize}"
                    ),
                    "cylindre_dents": round(developpe / 3.175) if developpe > 0 else 0,
                    "developpe_mm": round(developpe, 2),
                    "machine": nom_par_mach.get(c.machine_id, f"#{c.machine_id}"),
                    "poses_laize": c.nb_poses_laize,
                    "poses_dev": c.nb_poses_dev,
                    "poses_total": c.nb_poses_total,
                    "delta_dev_mm": round(c.intervalle_dev_reel_mm, 2),
                    "delta_laize_mm": round(c.intervalle_laize_reel_mm, 2),
                    "sens": _CONFIG_SENS_DEFAUT,
                    "score": round(c.score, 2),
                    "recommande": i < _CONFIG_TOP_RECOMMANDE,
                }
            )
        ecarts = {
            "intervalle_laize_mm": _ECART_INTERVALLE_LAIZE_MM,
            "intervalle_dev_mm": round(out.intervalle_dev_min_applique_mm, 2),
            "nb_poses_laize": "auto",
            "force_intervalle_laize": False,
        }
        return configs, ecarts
    except (OptimisationLoaderError, ValueError, KeyError):
        return [], None


def preview_devis(
    db: Session, entreprise_id: int, p: dict[str, Any]
) -> dict:
    """Recalc live READ-ONLY de la page unique (POST /api/devis/preview).

    Reçoit l'état PARTIEL du devis, renvoie les valeurs dérivées + prix SANS
    persister (aucun db.add). RÉUTILISE le cost_engine (`MoteurDevis`),
    `bat_calculs` (Ø) et le module refente — ZÉRO logique dupliquée. Champs
    manquants → calcul best-effort + alertes, jamais de 500. Idempotent.

    `prix_ht` = prix de vente des 7 postes (base PURE, sacrée) ; la refente
    (mode sans outil) est une ligne ADDITIVE de `decompo`, hors `prix_ht`.
    """
    _INTERVALLE_DEV = 2.0
    _INTERVALLE_LAIZE = 3.0
    alertes: list[dict] = []
    geometrie = {
        "diametre_mm": None,
        "nb_poses": None,
        "nb_filles": None,
        "dechet_lateral_mm": None,
    }
    out: dict = {
        "prix_ht": None,
        "cout_revient": None,
        "marge_pct": None,
        "prix_1000": None,
        "remise_pct": Decimal(str(p.get("remise_pct") or 0)),
        "remise_eur": None,
        "prix_ht_net": None,
        "decompo_groupee": None,
        "geometrie": geometrie,
        "decompo": [],
        "options": [],
        "alertes": alertes,
    }

    mode_sans_outil = bool(p.get("mode_sans_outil"))
    laize = p.get("laize")
    dev = p.get("dev")
    quantite = p.get("quantite")

    # Machine (P5) : id fourni (scopé tenant) sinon 1ère presse active.
    machine = None
    if p.get("machine_id"):
        machine = (
            db.query(Machine)
            .filter_by(id=p["machine_id"], entreprise_id=entreprise_id, actif=True)
            .first()
        )
        if machine is None:
            alertes.append(
                {"niveau": "warn", "message": "Machine introuvable/hors périmètre — 1ère presse utilisée."}
            )
    if machine is None:
        machine = (
            db.query(Machine)
            .filter_by(entreprise_id=entreprise_id, actif=True, type_machine="presse")
            .order_by(Machine.id)
            .first()
        )
    if machine is None:
        alertes.append(
            {"niveau": "warn", "message": "Aucune presse active — chiffrage indisponible."}
        )

    cyl = (
        db.get(CylindreMagnetique, p["cylindre_id"])
        if p.get("cylindre_id")
        else None
    )
    if p.get("cylindre_id") and cyl is None:
        alertes.append(
            {"niveau": "warn", "message": "Cylindre introuvable dans le parc."}
        )

    laize_utile = None
    if machine is not None:
        laize_utile = float(
            machine.laize_utile_mm
            if machine.laize_utile_mm is not None
            else machine.laize_max_mm
        )

    # Poses dérivées (best-effort) — l'état partiel ne porte pas les poses.
    nb_poses_dev = 1
    nb_poses_laize = 1
    if cyl is not None and dev:
        nb_poses_dev = max(
            1, math.floor(float(cyl.developpe_mm) / (float(dev) + _INTERVALLE_DEV))
        )
    if laize_utile and laize:
        nb_poses_laize = max(
            1, math.floor(laize_utile / (float(laize) + _INTERVALLE_LAIZE))
        )

    lot = LotProduction(
        entreprise_id=entreprise_id,
        ordre=1,
        cylindre_id=(cyl.id if cyl is not None else None),
        machine_id=(machine.id if machine is not None else 0),
        nb_poses_dev=nb_poses_dev,
        nb_poses_laize=nb_poses_laize,
        sens_enroulement=1,
        quantite=(quantite or 0),
        matiere_id=(p.get("matiere_id") or 1),
        intervalle_laize_reel_mm=Decimal(str(_INTERVALLE_LAIZE)),
        mode_sans_outil=mode_sans_outil,
        laize_stock_mm=(
            Decimal(str(p["laize_stock_mm"])) if p.get("laize_stock_mm") else None
        ),
        nb_filles_force=p.get("nb_filles_force"),
    )
    payload_input = {
        "format_etiquette_largeur_mm": int(laize) if laize else 60,
        "format_etiquette_hauteur_mm": int(dev) if dev else 40,
    }

    # nb_couleurs → P2 Encres + P3a clichés (réutilise le mapping existant).
    nb_couleurs_par_type = (
        _mapper_nb_couleurs(NbCouleursIn(**p["nb_couleurs"]))
        if p.get("nb_couleurs")
        else None
    )
    # Catalogue options du tenant (codes -> OptionFabrication, source unique de
    # coût). `finitions:[{montant_eur}]` reste accepté (DÉPRÉCIÉ, rétro-compat).
    catalogue = _catalogue_options(db, entreprise_id)
    forfaits_finitions = [
        PartenaireSTForfait(
            partenaire_st_id=int(f.get("partenaire_st_id") or 1),
            montant_eur=Decimal(str(f["montant_eur"])),
        )
        for f in (p.get("finitions") or [])
    ]

    # V0 — marge override (en %, levier live) → fraction `pct_marge_override`
    # du DevisInput (None = défaut tenant `ConfigCouts.marge_standard_pct`). Le
    # cost_engine reste SEUL juge du prix ; on ne fait que lui passer la marge.
    marge_override_frac = (
        (Decimal(str(p["marge_pct"])) / Decimal(100))
        if p.get("marge_pct") is not None
        else None
    )

    # === Bloc coût (7 postes) — RÉUTILISE _construire + MoteurDevis ===
    def _run(ncpt, forfaits):
        """Construit le DevisInput (best-effort) + lance MoteurDevis. Le moteur
        n'est PAS modifié — on ne fait que varier ses entrées."""
        di = _construire_devis_input_pour_lot(
            lot, payload_input, db, entreprise_id, ncpt
        )
        maj: dict = {}
        if forfaits:
            maj["forfaits_st"] = forfaits
        if marge_override_frac is not None:
            maj["pct_marge_override"] = marge_override_frac
        if maj:
            di = di.model_copy(update=maj)
        return MoteurDevis(db, entreprise_id).calculer(di), di

    devis_input = None
    if machine is not None and quantite:
        try:
            # 1er run (finitions ST seules) -> surface pour le pricing m²/mille.
            res0, devis_input = _run(nb_couleurs_par_type, forfaits_finitions)
            surface_m2 = (
                Decimal(devis_input.laize_utile_mm) / Decimal(1000)
                * Decimal(devis_input.ml_total)
            )

            # Options SÉLECTIONNÉES (codes) -> € serveur -> forfaits P6. Les
            # options sans € (impact production) sont ignorées du prix (rendues
            # dans `options[]` avec le flag, jamais en faux « +0 € »).
            options_appliquees: list[tuple[str, Decimal]] = []
            forfaits_options: list[PartenaireSTForfait] = []
            for code in (p.get("options_codes") or []):
                opt = catalogue.get(code)
                if opt is None:
                    alertes.append(
                        {"niveau": "warn", "message": f"Option inconnue : {code}."}
                    )
                    continue
                cout, _impact = _option_cout_eur(opt, surface_m2, quantite)
                if cout is not None and cout > 0:
                    forfaits_options.append(
                        PartenaireSTForfait(partenaire_st_id=1, montant_eur=cout)
                    )
                    options_appliquees.append((opt.libelle, cout))

            forfaits_all = forfaits_finitions + forfaits_options
            res = res0
            if forfaits_options:
                res, devis_input = _run(nb_couleurs_par_type, forfaits_all)

            base_prix = res.prix_vente_ht_eur
            marge = res.pct_marge_appliquee
            out["prix_ht"] = base_prix
            out["cout_revient"] = res.cout_revient_eur
            out["marge_pct"] = (marge * Decimal(100)).quantize(Decimal("0.01"))
            out["prix_1000"] = res.prix_au_mille_eur

            # V0 — remise tracée À PART (par-dessus le HT brut, hors coût).
            out["remise_eur"], out["prix_ht_net"] = _appliquer_remise(
                base_prix, out["remise_pct"]
            )

            # V0 — décompo COÛT regroupée (5 lignes métier). refente ajoutée
            # plus bas si mode sans outil. Somme = coût de revient (+ refente).
            par_poste = {pst.poste_numero: pst.montant_eur for pst in res.postes}
            out["decompo_groupee"] = {
                "matiere_p1": par_poste.get(1, Decimal("0")),
                "impression_presse_calage": (
                    par_poste.get(2, Decimal("0"))
                    + par_poste.get(4, Decimal("0"))
                    + par_poste.get(5, Decimal("0"))
                    + par_poste.get(7, Decimal("0"))
                ),
                "cliches_outil": par_poste.get(3, Decimal("0")),
                "option_finitions": par_poste.get(6, Decimal("0")),
                "refente": Decimal("0"),
            }

            # Décompo : 7 postes ; on ISOLE les options de la ligne Finitions
            # (label distinct, pas mélangées avec la sous-traitance).
            cout_options = sum((c for _, c in options_appliquees), Decimal("0"))
            for pst in res.postes:
                montant = pst.montant_eur
                if pst.poste_numero == 6 and cout_options > 0:
                    montant = (montant - cout_options).quantize(Decimal("0.01"))
                out["decompo"].append({"poste": pst.libelle, "montant": montant})
            for libelle, c in options_appliquees:
                out["decompo"].append({"poste": f"Option · {libelle}", "montant": c})

            # === options[] : delta marginal PAR CODE sur le catalogue tenant.
            # Additif (€) -> delta direct = € × (1 + marge) (pas de re-run du
            # moteur). Impact production (sans €) -> delta None + flag.
            facteur = Decimal(1) + marge
            for code, opt in catalogue.items():
                cout, impact = _option_cout_eur(opt, surface_m2, quantite)
                if cout is not None and cout > 0:
                    out["options"].append(
                        {
                            "code": code,
                            "delta_eur": (cout * facteur).quantize(Decimal("0.01")),
                            "impact_production": False,
                        }
                    )
                elif impact:
                    out["options"].append(
                        {"code": code, "delta_eur": None, "impact_production": True}
                    )
            # Delta d'une couleur process en plus (re-run : touche P2 + P3a).
            try:
                ncpt_plus = dict(nb_couleurs_par_type or {})
                ncpt_plus["process_cmj"] = ncpt_plus.get("process_cmj", 0) + 1
                res_plus, _ = _run(ncpt_plus, forfaits_all)
                out["options"].append(
                    {
                        "code": "couleur_plus",
                        "delta_eur": (
                            res_plus.prix_vente_ht_eur - base_prix
                        ).quantize(Decimal("0.01")),
                        "impact_production": False,
                    }
                )
            except (CostEngineError, ValueError):
                pass
        except (CostEngineError, ValueError) as exc:
            alertes.append(
                {"niveau": "warn", "message": f"Chiffrage partiel indisponible : {exc}"}
            )
    elif quantite is None:
        alertes.append(
            {"niveau": "info", "message": "Quantité manquante — coûts non chiffrés."}
        )

    # === Géométrie : Ø (bat_calculs), nb_poses, nb_filles, déchet ===
    if devis_input is not None:
        laize_pap = (
            float(devis_input.laize_papier_mm)
            if devis_input.laize_papier_mm is not None
            else float(devis_input.laize_utile_mm)
        )
        try:
            geometrie["diametre_mm"] = calcul_diametre_bobine(
                devis_input.ml_total,
                p.get("epaisseur_um") or 150,
                p.get("mandrin_mm") or 76,
                laize_pap,
            )
        except (ValueError, ArithmeticError):
            pass

    if mode_sans_outil:
        if machine is not None and laize and dev and quantite and p.get("laize_stock_mm"):
            try:
                geo = calculer_geometrie_sans_outil(
                    laize_stock_mm=float(p["laize_stock_mm"]),
                    laize_utile_presse_mm=laize_utile or float(p["laize_stock_mm"]),
                    format_largeur_mm=float(laize),
                    format_hauteur_mm=float(dev),
                    intervalle_laize_mm=_INTERVALLE_LAIZE,
                    quantite=int(quantite),
                    nb_filles_force=p.get("nb_filles_force"),
                )
                if geo is not None:
                    geometrie["nb_filles"] = geo.nb_filles
                    geometrie["nb_poses"] = geo.nb_filles
                    geometrie["dechet_lateral_mm"] = round(geo.dechet_lateral_mm, 2)
            except (ValueError, ArithmeticError):
                pass
        else:
            alertes.append(
                {"niveau": "info", "message": "Mode sans outil : laize stock + format requis pour le déchet."}
            )
        # Ligne refente ADDITIVE (RÉUTILISE _calculer_refente_lots).
        try:
            devis_tmp = Devis(entreprise_id=entreprise_id, client_id=None)
            refente = _calculer_refente_lots(
                db, devis_tmp, [lot], payload_input, entreprise_id
            )
            if refente and refente.get("applique"):
                refente_eur = Decimal(refente["cout_total_refente_eur"])
                out["decompo"].append(
                    {
                        "poste": "Refente (rebobinage)",
                        "montant": refente_eur,
                    }
                )
                # V0 — ligne refente de la décompo groupée.
                if isinstance(out.get("decompo_groupee"), dict):
                    out["decompo_groupee"]["refente"] = refente_eur
                alertes.append(
                    {
                        "niveau": "info",
                        "message": (
                            f"Refente : {refente['cout_total_refente_eur']} € "
                            "(additif, hors prix HT 7 postes)."
                        ),
                    }
                )
        except (CostEngineError, ValueError):
            pass
    else:
        if cyl is not None:
            geometrie["nb_poses"] = nb_poses_dev * nb_poses_laize
        elif not p.get("cylindre_id"):
            alertes.append(
                {"niveau": "info", "message": "Cylindre non sélectionné — nb poses non calculé."}
            )

    if not p.get("matiere_id"):
        alertes.append(
            {"niveau": "info", "message": "Matière non sélectionnée — complexe par défaut utilisé."}
        )

    # Lot C — configurations cylindre × machine + écarts (géométrie/lecture
    # pure via optimiser_pose, SSOT ; AUCUN coût touché).
    out["configs"], out["ecarts"] = _configs_preview(db, entreprise_id, p)

    return out


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

    # Lot back B — ligne de coût refente ADDITIVE (lots « sans outil »). Émise
    # au chiffrage. None si rien à facturer (config neutre / avec outil) →
    # value-neutral, sacrés intouchés.
    refente = _calculer_refente_lots(db, devis, lots, payload_input, entreprise_id)
    if refente is not None:
        po["refente"] = refente
    devis.payload_output = po

    # ht_total = base cost_engine + contribution rebobinage + refente (toutes
    # ADDITIVES, hors des 7 postes figés). À la création sans rebobinage ni
    # refente → ht_total = base (tripwire/benchmark inchangés).
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


# Ø mandrin par défaut (mm) si le tenant n'a pas de paramètre dédié — valeur
# flexo standard, sert uniquement à dimensionner l'axe Ø de la refente.
_MANDRIN_DEFAUT_MM = 76
# Épaisseur matière de repli (mm) si la matière du lot ne porte pas d'épaisseur.
_EPAISSEUR_REPLI_MM = Decimal("0.15")


def _calculer_refente_lots(
    db: Session,
    devis: Devis,
    lots: list[LotProduction],
    payload_input: dict[str, Any],
    entreprise_id: int,
) -> dict | None:
    """Lot back B — ligne de coût refente ADDITIVE pour les lots « sans outil ».

    Émise au chiffrage (AUTO). Réutilise le module rebobinage Sprint-16
    (axe Ø `calculer_bobines`) et MULTIPLIE par le `nb_filles` RÉSOLU (lot
    back A : géométrie + `nb_filles_force`, JAMAIS `nb_poses_laize`). Coût =
    temps refente × `ConfigCouts.cout_exploitation_rebobineuse_eur_h` + gâche
    raccord. `prix_vente_ht` (7 postes) et le calage restent INTOUCHÉS.

    Best-effort / gracieux : si la config est neutre (taux & gâche = 0), si
    aucune rebobineuse, ou si la géométrie Ø d'un lot est invalide → la ligne
    est simplement absente / le lot est ignoré (jamais d'erreur bloquante).
    Retourne None quand il n'y a rien à facturer (value-neutral).
    """
    from app.models import MachineRebobineuse, Matiere, ParametreMandrin
    from app.services.rebobinage.calcul_bobines import calculer_bobines
    from app.services.rebobinage.refente import calculer_cout_refente
    from app.services.rebobinage.types import ProfilClient, SpecLot

    lots_sans_outil = [lot for lot in lots if getattr(lot, "mode_sans_outil", False)]
    if not lots_sans_outil:
        return None

    cfg = (
        db.query(ConfigCouts).filter_by(entreprise_id=entreprise_id).first()
    )
    if cfg is None:
        return None
    taux = Decimal(str(cfg.cout_exploitation_rebobineuse_eur_h))
    gache_pct = Decimal(str(cfg.gache_raccord_pct))
    # Config neutre (rien configuré) → aucune ligne refente (value-neutral).
    if taux == 0 and gache_pct == 0:
        return None

    rebobineuse = (
        db.query(MachineRebobineuse)
        .filter_by(entreprise_id=entreprise_id, actif=True)
        .order_by(MachineRebobineuse.id)
        .first()
    )
    if rebobineuse is None:
        return {
            "applique": False,
            "raison": "aucune rebobineuse active — refente non chiffrée",
            "cout_total_refente_eur": "0.00",
            "lots": [],
        }

    # Profil client (Ø) : Ø max bobine du client si défini, sinon Ø max
    # rebobineuse ; Ø mandrin depuis ParametreMandrin, sinon défaut flexo.
    pm = (
        db.query(ParametreMandrin).filter_by(entreprise_id=entreprise_id).first()
    )
    diam_mandrin = (
        int(pm.diametre_mandrin_mm)
        if pm is not None and getattr(pm, "diametre_mandrin_mm", None)
        else _MANDRIN_DEFAUT_MM
    )
    client = db.get(Client, devis.client_id) if devis.client_id else None
    diam_max = None
    if client is not None and client.diametre_max_bobine_mm:
        diam_max = int(client.diametre_max_bobine_mm)
    elif rebobineuse.diametre_max_mm:
        diam_max = int(rebobineuse.diametre_max_mm)

    format_h = int(payload_input.get("format_etiquette_hauteur_mm", 40))
    format_l = int(payload_input.get("format_etiquette_largeur_mm", 60))

    lignes: list[dict] = []
    cout_total = Decimal("0.00")
    for lot in lots_sans_outil:
        try:
            machine = db.get(Machine, lot.machine_id)
            laize_presse = float(
                machine.laize_utile_mm
                if machine is not None and machine.laize_utile_mm is not None
                else (machine.laize_max_mm if machine is not None else 0)
            )
            laize_stock = (
                float(lot.laize_stock_mm)
                if lot.laize_stock_mm is not None
                else laize_presse
            )
            interv = float(lot.intervalle_laize_reel_mm or 0)
            nb_filles_force = (
                int(lot.nb_filles_force)
                if lot.nb_filles_force and lot.nb_filles_force > 0
                else None
            )
            geo = calculer_geometrie_sans_outil(
                laize_stock_mm=laize_stock,
                laize_utile_presse_mm=laize_presse,
                format_largeur_mm=float(format_l),
                format_hauteur_mm=float(format_h),
                intervalle_laize_mm=interv,
                quantite=lot.quantite,
                nb_filles_force=nb_filles_force,
            )
            if geo is None or geo.nb_filles <= 1:
                # Pas de refente réelle (1 fille) → pas de poste fantôme.
                continue

            mat = db.get(Matiere, lot.matiere_id) if lot.matiere_id else None
            epaisseur_um = getattr(mat, "epaisseur_microns", None) if mat else None
            epaisseur_mm = (
                Decimal(str(epaisseur_um)) / Decimal(1000)
                if epaisseur_um
                else _EPAISSEUR_REPLI_MM
            )
            if diam_max is None or diam_max <= diam_mandrin:
                # Ø client/rebobineuse non exploitable → lot ignoré (gracieux).
                continue

            nb_etiq_fille = max(1, lot.quantite // geo.nb_filles)
            bobines = calculer_bobines(
                SpecLot(
                    nb_etiquettes_total=nb_etiq_fille,
                    intervalle_developpe_mm=Decimal(str(format_h)),
                    epaisseur_matiere_mm=epaisseur_mm,
                ),
                ProfilClient(
                    diametre_mandrin_mm=diam_mandrin,
                    diametre_max_bobine_mm=diam_max,
                ),
            )
            res = calculer_cout_refente(
                nb_filles=geo.nb_filles,
                longueur_par_fille_m=Decimal(str(geo.ml_total)),
                bobines_par_fille=bobines,
                vitesse_pratique_m_min=int(rebobineuse.vitesse_pratique_m_min),
                temps_changement_bobine_min=Decimal(
                    str(rebobineuse.temps_changement_bobine_min)
                ),
                cout_exploitation_rebobineuse_eur_h=taux,
                gache_raccord_pct=gache_pct,
            )
            if not res.applicable:
                continue
            cout_total += res.cout_refente_eur
            lignes.append(
                {
                    "ordre": lot.ordre,
                    "nb_filles": res.nb_filles,
                    "nb_bobines_total": res.nb_bobines_total,
                    "longueur_rebobinee_m": str(res.longueur_rebobinee_m),
                    "gache_metres": str(res.gache_metres),
                    "temps_refente_h": str(res.temps_refente_h),
                    "cout_refente_eur": str(res.cout_refente_eur),
                }
            )
        except (ValueError, ArithmeticError) as exc:  # noqa: BLE001
            logger.warning(
                "Refente lot %s non chiffrée (gracieux) : %s", lot.ordre, exc
            )
            continue

    if not lignes:
        return None
    return {
        "applique": True,
        "machine_rebobineuse_id": rebobineuse.id,
        "nb_lots_refendus": len(lignes),
        "cout_total_refente_eur": str(cout_total.quantize(Decimal("0.01"))),
        "lots": lignes,
    }


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
        # nb_filles RÉSOLU = géométrie + override opérateur `nb_filles_force`
        # (lot back A/B). On n'utilise JAMAIS `nb_poses_laize` (≠ filles : c'est
        # l'axe poses). NULL → dérivation géométrique auto.
        nb_filles_force_lot = (
            int(lot.nb_filles_force)
            if lot.nb_filles_force and lot.nb_filles_force > 0
            else None
        )
        geo = calculer_geometrie_sans_outil(
            laize_stock_mm=laize_stock,
            laize_utile_presse_mm=laize_presse,
            format_largeur_mm=float(format_l),
            format_hauteur_mm=float(format_h),
            intervalle_laize_mm=interv_laize,
            quantite=lot.quantite,
            nb_filles_force=nb_filles_force_lot,
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
        # `cylindre_id` None (état partiel preview) → message clair sans
        # `db.get(None)` (évite le SAWarning « fully NULL primary key »).
        if lot.cylindre_id is None:
            raise ValueError(
                "Cylindre requis pour chiffrer un lot avec outil."
            )
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
                # Lot back A/B — cylindre_id NULLABLE (sans outil).
                cylindre_id=lot_dict.get("cylindre_id"),
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
                # Lot back A/B — persistance du mode sans outil à l'édition.
                mode_sans_outil=lot_dict.get("mode_sans_outil", False),
                laize_stock_mm=lot_dict.get("laize_stock_mm"),
                nb_filles_force=lot_dict.get("nb_filles_force"),
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
