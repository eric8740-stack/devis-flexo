"""Schémas Pydantic — persistance Devis (Sprint 4 Lot 4b).

Distincts de `app/schemas/devis.py` (qui porte DevisInput/DevisOutput
du moteur cost_engine). Ici : DevisCreate / DevisUpdate / DevisListItem /
DevisDetail / DevisListResponse pour les endpoints CRUD /api/devis.

PK Integer (homogène projet) — divergence vs brief UUID assumée Lot 4a.

Sprint 13 avenant : ajout LotProductionCreate / LotProductionRead +
champs optionnels `lots` et `quantite_totale` sur DevisCreate, et
`lots_production` sur DevisDetail. Backward-compat : si `lots` est
None, le devis est créé en mode legacy (mono-config, sans lot).
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LotProductionCreate(BaseModel):
    """Body d'un lot de production dans POST /api/devis (Sprint 13 avenant).

    Reflète les champs nécessaires pour créer une row LotProduction. Les
    résultats calculés (intervalles, score, coût) seront snapshotés par
    le router à partir des données candidat sélectionné.
    """

    model_config = ConfigDict(extra="forbid")

    cylindre_id: int
    machine_id: int
    nb_poses_dev: int = Field(ge=1)
    nb_poses_laize: int = Field(ge=1)
    sens_enroulement: int = Field(ge=0, le=9)
    quantite: int = Field(ge=1)
    matiere_id: int

    # Optionnels : snapshot des résultats moteur pour PDF / historique.
    intervalle_dev_reel_mm: Decimal | None = None
    intervalle_laize_reel_mm: Decimal | None = None
    largeur_plaque_mm: Decimal | None = None
    score_optim: float | None = None
    cout_lot_ht_eur: Decimal | None = None

    # Brief #33 — snapshot visuel pour SchemaImplantation par lot (laize
    # papier, liner, chute latérale, diamètre bobine, lacets, rotations).
    # Stocké tel quel en JSONB côté DB.
    payload_visuel: dict | None = None


class LotProductionRead(BaseModel):
    """Représentation lecture d'un lot dans GET /api/devis/{id} (Sprint 13).

    Brief #32 commit 3 : enrichi avec les jointures les plus utiles pour
    l'UI (machine_nom, cylindre_nb_dents, matiere_libelle, rotation_se
    pour visuel) afin d'éviter N+1 côté frontend.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    ordre: int
    cylindre_id: int
    machine_id: int
    nb_poses_dev: int
    nb_poses_laize: int
    sens_enroulement: int
    quantite: int
    matiere_id: int
    intervalle_dev_reel_mm: Decimal | None
    intervalle_laize_reel_mm: Decimal | None
    largeur_plaque_mm: Decimal | None
    score_optim: float | None
    cout_lot_ht_eur: Decimal | None
    created_at: datetime
    updated_at: datetime

    # Brief #32 — joints pour l'UI multi-lots. Défauts à None pour
    # rester rétro-compatible avec les rows historiques (créées sans
    # population des joints, par exemple via migration).
    machine_nom: str | None = None
    cylindre_nb_dents: int | None = None
    cylindre_developpe_mm: Decimal | None = None
    matiere_libelle: str | None = None
    sens_enroulement_libelle: str | None = None
    rotation_vue_a_deg: int | None = None
    rotation_vue_c_deg: int | None = None

    # Brief #33 — snapshot visuel JSON (laize papier, liner, chute latérale,
    # diamètre bobine, lacets...). Null pour lots historiques.
    payload_visuel: dict | None = None


class NbCouleursIn(BaseModel):
    """Sprint 16 fix chiffrage — compteurs de couleurs du devis.

    Alimente le Poste 2 Encres du cost_engine (via mapping vers les
    `type_encre` réels en base). Champs à 0 par défaut (rétro-compatible :
    un payload sans `nb_couleurs` → P2 Encres = 0, comportement antérieur).

    Mapping côté CRUD vers `nb_couleurs_par_type` :
      - impression → "process_cmj"   (process quadri)
      - pantone    → "pantone"
      - blanc      → "blanc_high_opaque"
      - vernis     → NON mappé (le vernis est une finition P6, pas une encre P2)
    """

    model_config = ConfigDict(extra="forbid")

    impression: int = Field(default=0, ge=0)
    pantone: int = Field(default=0, ge=0)
    blanc: int = Field(default=0, ge=0)
    vernis: int = Field(default=0, ge=0)


class DevisCreate(BaseModel):
    """Body POST /api/devis.

    payload_input et payload_output sont validés côté client (déjà passés
    par le moteur cost_engine via /api/cost/calculer). Stockés en JSON
    pour flexibilité MVP.

    Sprint 13 avenant : `lots` et `quantite_totale` sont optionnels.
    Si fournis ensemble, le devis créé porte N LotProduction et la
    somme des quantités par lot doit égaler quantite_totale (validé).
    Si `lots` est None, comportement legacy mono-config inchangé.
    """

    model_config = ConfigDict(extra="forbid")

    payload_input: dict
    payload_output: dict
    client_id: int | None = None
    statut: Literal["brouillon", "valide"] = "brouillon"
    # Mode matching : cylindre choisi parmi les 3 candidats (UI Lot 4d).
    cylindre_choisi_z: int | None = None
    cylindre_choisi_nb_etiq: int | None = None

    # Sprint 13 avenant — multi-lots (optionnel pour backward-compat).
    quantite_totale: int | None = Field(None, ge=1)
    lots: list[LotProductionCreate] | None = Field(None, min_length=1)

    # Sprint 14 Lot 1 — brief client unifié (caractérise la livraison
    # finale, commune à tous les lots du devis). Tous optionnels avec
    # defaults rétro-compatibles : un payload pré-S14 reste valide.
    nb_etiquettes_par_rouleau: int | None = Field(None, ge=1)
    diametre_max_bobine_mm: int | None = Field(None, ge=1)
    nb_fronts_sortie: int | None = Field(1, ge=1)
    type_entree_fichier: Literal[
        "vierge", "bat_pro_fourni", "a_designer"
    ] = "a_designer"
    conditions_stockage: dict | None = None

    # Sprint 16 fix chiffrage — compteurs couleurs pour le Poste 2 Encres.
    # Optionnel : None → P2 Encres = 0 (comportement antérieur préservé).
    # CC2 enverra ce champ depuis le store optim (nb couleurs saisi étape 1).
    nb_couleurs: NbCouleursIn | None = None

    @model_validator(mode="after")
    def _valider_somme_quantites_lots(self) -> "DevisCreate":
        """Si des lots sont fournis, leur somme de quantités doit égaler
        `quantite_totale` (cf brief Sprint 13 avenant section 7).

        `quantite_totale` doit être fourni quand `lots` est fourni
        (sinon on ne sait pas valider la cohérence).
        """
        if self.lots is not None:
            if self.quantite_totale is None:
                raise ValueError(
                    "Multi-lots : quantite_totale obligatoire quand lots est fourni."
                )
            total = sum(lot.quantite for lot in self.lots)
            if total != self.quantite_totale:
                raise ValueError(
                    f"Multi-lots : Σ quantités lots ({total}) "
                    f"!= quantite_totale ({self.quantite_totale})."
                )
        return self


class DevisUpdate(BaseModel):
    """Body PUT /api/devis/{id} — partial update via exclude_unset.

    Brief #32 commit 2 : ajout `reduction_pct` (0..100 %) + `lots`
    optionnel (si fourni, recalcule cost_engine_aggregator côté CRUD).
    """

    model_config = ConfigDict(extra="forbid")

    payload_input: dict | None = None
    payload_output: dict | None = None
    client_id: int | None = None
    statut: Literal["brouillon", "valide"] | None = None
    cylindre_choisi_z: int | None = None
    cylindre_choisi_nb_etiq: int | None = None

    # Brief #32 — réduction commerciale (0..100). Le brut reste dans
    # `payload_output.prix_vente_ht_eur` ; l'UI calcule l'après-remise.
    reduction_pct: Decimal | None = Field(None, ge=0, le=100)

    # Brief #32 — lots éditables. Si fourni, replace TOUS les lots du
    # devis (delete cascade existing + insert news), puis recalcule
    # cost_engine_aggregator.
    quantite_totale: int | None = Field(None, ge=1)
    lots: list[LotProductionCreate] | None = Field(None, min_length=1)

    # Sprint 14 Lot 1 — brief client unifié. Tous None par défaut (partial
    # update via exclude_unset côté CRUD : seuls les champs effectivement
    # transmis sont écrits).
    nb_etiquettes_par_rouleau: int | None = Field(None, ge=1)
    diametre_max_bobine_mm: int | None = Field(None, ge=1)
    nb_fronts_sortie: int | None = Field(None, ge=1)
    type_entree_fichier: Literal[
        "vierge", "bat_pro_fourni", "a_designer"
    ] | None = None
    conditions_stockage: dict | None = None


class DevisListItem(BaseModel):
    """Item retourné par GET /api/devis (liste paginée)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    date_creation: datetime
    statut: str
    client_id: int | None
    client_nom: str | None
    machine_id: int
    machine_nom: str
    format_h_mm: Decimal
    format_l_mm: Decimal
    # Sprint 16 fix chiffrage : Optional — un devis "chiffrage incomplet"
    # (option B) a ht_total_eur NULL, distinct d'un 0 € trompeur.
    ht_total_eur: Decimal | None
    mode_calcul: str


class DevisDetail(BaseModel):
    """Détail GET /api/devis/{id} + retour POST/PUT/duplicate."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    date_creation: datetime
    date_modification: datetime
    statut: str
    client_id: int | None
    client_nom: str | None
    machine_id: int
    machine_nom: str
    payload_input: dict
    payload_output: dict
    mode_calcul: str
    cylindre_choisi_z: int | None
    cylindre_choisi_nb_etiq: int | None
    format_h_mm: Decimal
    format_l_mm: Decimal
    # Sprint 16 fix chiffrage : Optional — devis "chiffrage incomplet"
    # (option B) → ht_total_eur NULL au lieu d'un 0 € trompeur.
    ht_total_eur: Decimal | None
    # Brief #32 — réduction commerciale (default 0, voir CRUD).
    reduction_pct: Decimal = Decimal(0)
    # Sprint 13 avenant — lots de production (liste vide si devis legacy
    # mono-config).
    lots_production: list[LotProductionRead] = Field(default_factory=list)

    # Sprint 14 Lot 1 — brief client unifié. Defaults rétro-compatibles
    # avec les devis pré-S14 : la migration a posé `a_designer` et `1`
    # via server_default, les autres restent NULL.
    nb_etiquettes_par_rouleau: int | None = None
    diametre_max_bobine_mm: int | None = None
    nb_fronts_sortie: int | None = 1
    type_entree_fichier: str = "a_designer"
    conditions_stockage: dict | None = None


class DevisListResponse(BaseModel):
    """Pagination GET /api/devis."""

    items: list[DevisListItem]
    total: int
    page: int
    per_page: int
    pages: int


# ---------------------------------------------------------------------------
# Brief #33 — endpoint POST /api/devis/preview-couts
# ---------------------------------------------------------------------------
# Calcule brut/réduction/net sans persister. Sert au recalcul live de
# l'étape 4 chiffrage (toggle options, ajustement marge/réduction).


class PreviewCoutsIn(BaseModel):
    """Body POST /api/devis/preview-couts (Brief #33)."""

    model_config = ConfigDict(extra="forbid")

    # payload_input : contexte saisie (laize/dev, options, marge override).
    payload_input: dict
    lots: list[LotProductionCreate] = Field(min_length=1)
    reduction_pct: Decimal = Field(default=Decimal(0), ge=0, le=100)
    # Sprint 16 fix chiffrage — compteurs couleurs pour le preview live.
    nb_couleurs: NbCouleursIn | None = None


class PreviewCoutsOut(BaseModel):
    """Réponse POST /api/devis/preview-couts.

    `cout_brut_ht` = somme du cost_engine_aggregator sans réduction.
    `cout_net_ht` = brut × (1 - reduction_pct/100).
    """

    model_config = ConfigDict(extra="forbid")

    # Sprint 16 fix chiffrage : montants Optional. Quand
    # `chiffrage_auto_erreur` est non-null (ex: matière non reliée à un
    # complexe), les montants valent None — jamais un 0 € trompeur. L'UI
    # affiche "chiffrage indisponible" au lieu d'un faux prix nul.
    cout_brut_ht_eur: Decimal | None
    reduction_pct: Decimal
    reduction_eur: Decimal | None
    cout_net_ht_eur: Decimal | None
    nb_lots: int
    # Nom de champ unifié avec la réponse POST /devis (payload_output.
    # chiffrage_auto_erreur) — CC2 consomme ce nom exact pour le bandeau.
    chiffrage_auto_erreur: str | None = None


# ---------------------------------------------------------------------------
# Cohérence Ø ext ↔ nb étiquettes/bobine — endpoint stateless live UI
# ---------------------------------------------------------------------------

class CoherenceBobineRequest(BaseModel):
    """Inputs du check de cohérence bobine (saisie devis, étape brief).

    Stateless : aucune persistance. Les valeurs viennent du formulaire
    brief client (Ø saisi, nb étiq saisi) et du contexte saisie
    (`pas_mm = dev_etiq + ecart_dev`, mandrin, épaisseur catalogue).
    """

    model_config = ConfigDict(extra="forbid")

    diametre_ext_saisi_mm: float = Field(gt=0, le=2000)
    nb_etiq_saisi: int = Field(ge=1)
    mandrin_mm: int = Field(gt=0, le=500)
    pas_mm: float = Field(gt=0, le=1000)
    # Épaisseur catalogue matière. Si None, le service applique le
    # fallback EPAISSEUR_FALLBACK_UM (150 µm) et signale la source.
    epaisseur_catalogue_um: float | None = Field(default=None, gt=0, le=10000)
    # Ø max accepté par la machine de pose du client (profil sprint 16).
    # Si fourni, déclenche le check « fit » physique (Ø saisi > Ø max).
    diametre_max_client_mm: float | None = Field(default=None, gt=0, le=2000)
    # Tolérance d'acceptabilité (% du nb_max). Param entreprise plus tard.
    tolerance_pct: float = Field(default=3.0, ge=0, le=50)


class CoherenceBobineResponse(BaseModel):
    """Résultat du check : alerte agrégée + valeurs cohérentes (actionables)."""

    model_config = ConfigDict(extra="forbid")

    severity: Literal["ok", "info", "warning"]
    message: str
    nb_max: int
    diametre_requis_mm: int
    fit_severity: Literal["ok", "warning"] | None
    fit_message: str | None
    epaisseur_appliquee_um: float
    epaisseur_source: Literal["catalogue", "fallback"]


# ---------------------------------------------------------------------------
# Planificateur de bobines — 3 (ou 4) scénarios de découpe, rapport de fab
# ---------------------------------------------------------------------------

class TarifsMandrinsIn(BaseModel):
    """Tarifs mandrins (pré-coupé vs découpe interne) — input request."""

    model_config = ConfigDict(extra="forbid")
    prix_pre_coupe_par_mandrin_eur: Decimal = Field(ge=0)
    cout_decoupe_interne_par_mandrin_eur: Decimal = Field(ge=0)
    cout_fixe_decoupe_interne_eur: Decimal = Field(ge=0)


class PlanificateurBobinesRequest(BaseModel):
    """Inputs du planificateur de bobines.

    Stateless : aucune persistance. Cost rebobinage calculé en lecture
    seule via les helpers existants si machine + tarifs fournis ; sinon
    on retourne les scénarios sans coût (l'UI affiche juste géométrie +
    surprod).
    """

    model_config = ConfigDict(extra="forbid")

    # Inputs géométriques — Q post-optim et n_laize lu du lot.
    quantite_commandee: int = Field(ge=1)
    n_laize: int = Field(ge=1)
    pas_mm: float = Field(gt=0, le=1000)
    mandrin_mm: int = Field(gt=0, le=500)
    diametre_max_bobine_mm: float = Field(gt=0, le=2000)
    epaisseur_matiere_um: float = Field(gt=0, le=10000)
    # Scénario imposé — anti-fléau. Si None, pas de carte IMPOSE/alerte.
    nb_etiq_impose: int | None = Field(default=None, ge=1)
    # Cost rebobinage (LECTURE SEULE moteur). Optionnels — sans, pas de coût.
    machine_rebobineuse_id: int | None = None
    tarifs_mandrins: TarifsMandrinsIn | None = None


class RepartitionBobineOut(BaseModel):
    """Un groupe de bobines identiques dans un scénario."""

    model_config = ConfigDict(extra="forbid")
    nb_etiq_par_bobine: int
    nb_bobines_par_piste: int
    diametre_mm: int


class ScenarioBobinesOut(BaseModel):
    """Un scénario complet, prêt pour l'UI."""

    model_config = ConfigDict(extra="forbid")
    cle: Literal["A", "B", "C_inf", "C_sup", "IMPOSE"]
    titre: str
    repartition: list[RepartitionBobineOut]
    nb_bobines_par_piste: int
    nb_bobines_total: int
    quantite_totale_etiq: int
    surprod_etiq: int
    q_ajustee: int | None
    # Coût rebobinage (None si machine/tarifs absents — lecture seule).
    cout_total_eur: Decimal | None
    cout_machine_eur: Decimal | None
    cout_mandrins_eur: Decimal | None
    mode_mandrins_optimal: Literal["pre_coupe", "decoupe_interne"] | None


class AlerteImposeOut(BaseModel):
    """Anti-fléau : diagnostics chiffrés quand client impose un nb/bobine."""

    model_config = ConfigDict(extra="forbid")
    nb_impose: int
    nb_realisable_max: int
    diametre_requis_mm: int
    physiquement_impossible: bool


class PlanificateurBobinesResponse(BaseModel):
    """Sortie complète planificateur : scénarios + reco + diagnostics."""

    model_config = ConfigDict(extra="forbid")
    scenarios: list[ScenarioBobinesOut]
    recommande_cle: Literal["A", "B", "C_inf", "C_sup"] | None
    nb_max_par_bobine: int
    pas_mm: float
    alerte_impose: AlerteImposeOut | None


# ---------------------------------------------------------------------------
# Persistance du choix planificateur — payload_input.plan_bobines (JSONB)
# ---------------------------------------------------------------------------

class PlanBobinesSelectionIn(BaseModel):
    """Selection du commercial à persister dans payload_input.plan_bobines.

    Écriture **ciblée** côté backend (merge partiel) : seul ce sous-objet
    est mis à jour, le reste de `payload_input` (sens_enroulement,
    nb_couleurs, options_codes_etape4, etc.) est strictement préservé.

    `force_diametre` + `motif_forcage` sont obligatoires ENSEMBLE quand
    le scénario IMPOSE dépasse la limite physique (`physiquement_impossible`
    déjà signalé par l'endpoint planificateur). Ils sont None sinon.
    """

    model_config = ConfigDict(extra="forbid")

    scenario: Literal["A", "B", "C_inf", "C_sup", "IMPOSE"]
    nb_bobine: int = Field(ge=1)  # nb d'étiq par bobine pleine (config retenue)
    nb_bobines_total: int = Field(ge=1)
    politique_reliquat: Literal["pleines_plus_reliquat", "equilibrees", "tomber_juste"]
    q_ajustee: int | None = Field(default=None, ge=1)
    force_diametre: bool | None = None
    motif_forcage: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _valider_forcage(self) -> "PlanBobinesSelectionIn":
        # Forçage et motif sont indissociables : si force_diametre=True,
        # motif obligatoire (≥ 1 caractère trimmé). Sans motif → on refuse
        # l'écriture (le commercial peut choisir, mais consciemment).
        if self.force_diametre:
            motif = (self.motif_forcage or "").strip()
            if not motif:
                raise ValueError(
                    "Forçage IMPOSE : motif obligatoire (traçabilité). "
                    "Décris pourquoi tu retiens un scénario physiquement "
                    "infaisable au Ø client."
                )
        return self


class PlanBobinesSelectionOut(BaseModel):
    """Retour après écriture : la sélection persistée telle quelle."""

    model_config = ConfigDict(extra="forbid")

    scenario: Literal["A", "B", "C_inf", "C_sup", "IMPOSE"]
    nb_bobine: int
    nb_bobines_total: int
    politique_reliquat: str
    q_ajustee: int | None = None
    force_diametre: bool | None = None
    motif_forcage: str | None = None
