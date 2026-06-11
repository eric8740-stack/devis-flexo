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

    # Lot back A/B — NULLABLE : un lot « mode sans outil » n'a pas d'outil de
    # découpe (cylindre). Reste requis de fait pour un lot avec outil (le front
    # le fournit), mais le schéma ne 422 plus en sans outil.
    cylindre_id: int | None = None
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

    # L1 — bord latéral surchargeable par lot (mm). NULL → défaut =
    # entreprise.chute_laterale_min_mm (comportement actuel).
    bord_lateral_mm: Decimal | None = None

    # Lot back A/B — mode « format sans outil » + persistance du flag. Défauts
    # NEUTRES (value-neutral) : un lot legacy/avec outil ne pose pas ces champs.
    mode_sans_outil: bool = False
    laize_stock_mm: Decimal | None = None
    # Lot back B — override opérateur du nb de filles de refente (≠ nb_poses_laize).
    nb_filles_force: int | None = None

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
    # Lot back A/B — NULLABLE en lecture (lot sans outil = pas de cylindre).
    cylindre_id: int | None = None
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

    # Lot back A/B — mode sans outil rechargé (le flag survit au reload du devis).
    mode_sans_outil: bool = False
    laize_stock_mm: Decimal | None = None
    nb_filles_force: int | None = None

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
# POST /api/devis/preview — recalc live read-only de la page unique
# ---------------------------------------------------------------------------


class FinitionPreviewIn(BaseModel):
    """Une finition sous-traitance du preview → mappée sur `forfaits_st` (P6).

    Réutilise la mécanique P6 existante (somme des forfaits ST). `montant_eur`
    pilote le coût ; chaque finition fait donc bouger le prix.
    """

    model_config = ConfigDict(extra="forbid")

    montant_eur: Decimal = Field(ge=0)
    partenaire_st_id: int = Field(default=1, gt=0)
    libelle: str | None = None


class DevisPreviewIn(BaseModel):
    """État PARTIEL du devis pour le recalc live (tous champs optionnels).

    Read-only : aucune persistance. Champs manquants → calcul best-effort,
    jamais de 500. Scopé `entreprise_id` côté router.
    """

    model_config = ConfigDict(extra="forbid")

    laize: float | None = Field(None, gt=0, description="Largeur étiquette (mm)")
    dev: float | None = Field(None, gt=0, description="Développé / hauteur (mm)")
    forme: str | None = Field(None, description="Forme (rectangle/spéciale/courbe)")
    quantite: int | None = Field(None, gt=0)
    cylindre_id: int | None = Field(None, gt=0)
    machine_id: int | None = Field(None, gt=0, description="Presse (P5). Défaut = 1ère active.")
    matiere_id: int | None = Field(None, gt=0)
    epaisseur_um: int | None = Field(None, gt=0)
    mandrin_mm: int | None = Field(None, gt=0)
    diam_max_mm: int | None = Field(None, gt=0)
    # Lot F — bobinage/appro (overrides, sinon défauts config). `ml_par_bobine`
    # → sinon Entreprise.ml_par_bobine_defaut ; `diametre_mandrin_mm` → défaut 76.
    ml_par_bobine: int | None = Field(None, gt=0)
    diametre_mandrin_mm: int | None = Field(None, gt=0)
    nb_filles_force: int | None = Field(None, ge=1)
    mode_sans_outil: bool = False
    laize_stock_mm: float | None = Field(None, gt=0)
    # Lot C-inputs — sélection de config + forçage des écarts (Règle 7). Défauts
    # (None/False) = comportement actuel STRICTEMENT inchangé.
    config_id: str | None = Field(
        None,
        max_length=64,
        description="Config choisie 'cyl-mach-DxL' → fige cylindre/machine/poses.",
    )
    force_intervalle_laize: bool = False
    intervalle_laize_mm: float | None = Field(None, gt=0, le=50)
    nb_poses_laize_force: int | None = Field(None, ge=1, le=20)
    # V0 — leviers commerciaux live. `marge_pct` (override, en %) → recalcul HT
    # (None = défaut tenant `ConfigCouts.marge_standard_pct`). `remise_pct` =
    # remise commerciale par-dessus le HT brut, N'ENTRE PAS dans le coût.
    marge_pct: Decimal | None = Field(None, ge=0, le=200)
    remise_pct: Decimal = Field(default=Decimal(0), ge=0, le=100)
    # nb_couleurs → P2 Encres + P3a clichés (réutilise NbCouleursIn + mapping).
    nb_couleurs: NbCouleursIn | None = None
    # options_codes : ENTRÉE CANONIQUE des options (le front a les codes via
    # /options-disponibles, jamais les montants). Le serveur résout le € depuis
    # OptionFabrication (catalogue tenant+global) → forfaits_st → P6.
    options_codes: list[str] = Field(default_factory=list)
    # DÉPRÉCIÉ (rétro-compat A1 en prod qui envoie []) : forfaits ST saisis à la
    # volée avec montant explicite. Préférer `options_codes`.
    finitions: list[FinitionPreviewIn] = Field(default_factory=list)


class GeometriePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diametre_mm: int | None = None
    nb_poses: int | None = None
    nb_filles: int | None = None
    dechet_lateral_mm: float | None = None
    # Lot E — épaisseur réelle utilisée pour le Ø + flag fallback (150 µm jamais
    # silencieux : `epaisseur_fallback=True` quand la matière n'a pas d'épaisseur).
    epaisseur_utilisee_microns: int | None = None
    epaisseur_fallback: bool = False


class BobinagePreview(BaseModel):
    """Lot F — bobinage + appro matière (géométrie/appro, AUCUN chiffrage).

    Convention bobine métier : laize × Ø × mandrin – longueur. `temps_arret_min`
    est AFFICHÉ (indicatif), JAMAIS facturé (la facturation du temps d'arrêt est
    un lot dédié ultérieur qui touchera le cost_engine). `None` quand l'état est
    trop partiel (pas de métrage matière) → dégradation propre côté front.
    """

    model_config = ConfigDict(extra="forbid")

    ml_total: float
    m2_total: float
    ml_par_bobine: int
    nb_bobines: int
    diametre_bobine_mm: int
    diametre_mandrin_mm: int
    diametre_max_presse_mm: int
    depasse_max: bool
    nb_changements: int
    temps_arret_min: int


class DecompoLignePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    poste: str
    montant: Decimal


class OptionDeltaPreview(BaseModel):
    """Impact marginal d'un levier activable (prix avec − prix sans, état
    courant). Calculé serveur, même réponse — pas d'appel séparé.

    `impact_production=True` + `delta_eur=None` : option à impact production
    (coef vitesse/gâche/temps calage) SANS forfait → pas encore chiffrée (le
    cost_engine ne price pas ces impacts en V1). Le front affiche « impact
    production (chiffré bientôt) », jamais un faux « +0 € »."""

    model_config = ConfigDict(extra="forbid")

    code: str
    delta_eur: Decimal | None = None
    impact_production: bool = False


class AlertePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    niveau: Literal["info", "warn"]
    message: str


class ConfigPreview(BaseModel):
    """Une configuration cylindre × machine (Lot C) — géométrie/lecture pure,
    issue du moteur `optimiser_pose` (SSOT). AUCUN coût."""

    model_config = ConfigDict(extra="forbid")

    id: str
    cylindre_dents: int
    developpe_mm: float
    machine: str
    poses_laize: int
    poses_dev: int
    poses_total: int
    delta_dev_mm: float
    delta_laize_mm: float
    sens: int
    score: float
    recommande: bool = False


class EcartsPreview(BaseModel):
    """Écarts entre étiquettes (Lot C). `nb_poses_laize` : "auto" ou un entier
    forcé. `force_intervalle_laize` : Règle 7 (souveraineté)."""

    model_config = ConfigDict(extra="forbid")

    intervalle_laize_mm: float
    intervalle_dev_mm: float
    nb_poses_laize: str | int = "auto"
    force_intervalle_laize: bool = False


class DecompoGroupee(BaseModel):
    """V0 — décompo COÛT regroupée en 5 lignes métier (panneau prix). Somme =
    coût de revient + refente. NON breaking : s'ajoute à `decompo` (liste plate)."""

    model_config = ConfigDict(extra="forbid")

    matiere_p1: Decimal
    impression_presse_calage: Decimal
    cliches_outil: Decimal
    option_finitions: Decimal
    refente: Decimal


class DevisPreviewOut(BaseModel):
    """Réponse POST /api/devis/preview.

    `prix_ht` = prix de vente HT des 7 postes (base PURE cost_engine, sacrée).
    `decompo` liste les 7 postes + une ligne « Refente » ADDITIVE en mode sans
    outil (le coût refente n'entre PAS dans `prix_ht`). Montants None quand
    l'état est trop partiel pour chiffrer (jamais un 0 € trompeur).
    """

    model_config = ConfigDict(extra="forbid")

    prix_ht: Decimal | None = None
    cout_revient: Decimal | None = None
    marge_pct: Decimal | None = None
    prix_1000: Decimal | None = None
    # V0 — remise commerciale TRACÉE À PART (par-dessus le HT brut, n'affecte pas
    # le coût). `prix_ht` reste le HT brut (7 postes, sacré) ; `prix_ht_net` =
    # HT facturé après remise.
    remise_pct: Decimal = Decimal(0)
    remise_eur: Decimal | None = None
    prix_ht_net: Decimal | None = None
    # V0 — décompo coût regroupée (5 lignes métier), en plus de `decompo` plate.
    decompo_groupee: DecompoGroupee | None = None
    geometrie: GeometriePreview
    # Lot F — bobinage + appro matière (géométrie/appro, AUCUN chiffrage). None
    # quand l'état est trop partiel pour un métrage matière.
    bobinage: BobinagePreview | None = None
    decompo: list[DecompoLignePreview] = Field(default_factory=list)
    # Impact marginal serveur de chaque levier activable (finition, +1 couleur).
    options: list[OptionDeltaPreview] = Field(default_factory=list)
    # Lot C — configurations cylindre × machine (tri score, top 3 recommandé)
    # + écarts entre étiquettes. Vide si géométrie incomplète / sans outil.
    configs: list[ConfigPreview] = Field(default_factory=list)
    ecarts: EcartsPreview | None = None
    alertes: list[AlertePreview] = Field(default_factory=list)


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
    epaisseur_source: Literal["matiere", "fallback"]


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
    # Scénarios imposés — anti-fléau. 3 modes mutuellement exclusifs :
    #   - `nb_etiq_impose` seul : étiq/bobine imposé, nb_bobines dérivé.
    #   - `nb_bobines_impose` seul : nb_bobines imposé, étiq/bobine dérivé.
    #   - `nb_bobines_impose + packaging_nb_etiq_par_bobine` : packaging
    #     complet (les deux imposés). Surplus + 3 options Q exposés.
    # Si tous None → pas de carte IMPOSE/alerte (scénarios A/B/C seuls).
    nb_etiq_impose: int | None = Field(default=None, ge=1)
    nb_bobines_impose: int | None = Field(default=None, ge=1)
    packaging_nb_etiq_par_bobine: int | None = Field(default=None, ge=1)
    # Cost rebobinage (LECTURE SEULE moteur). Optionnels — sans, pas de coût.
    machine_rebobineuse_id: int | None = None
    tarifs_mandrins: TarifsMandrinsIn | None = None

    @model_validator(mode="after")
    def _valider_modes_impose_mutex(self) -> "PlanificateurBobinesRequest":
        """Mutex : un seul mode IMPOSE actif à la fois.

        `packaging` = nb_bobines_impose ET packaging_nb_etiq_par_bobine.
        Sinon mode `nb_bobines` ou `nb_etiq` seul. Le mode mixte
        (nb_etiq + nb_bobines) est rejeté côté schema (422).
        """
        if self.nb_etiq_impose is not None and (
            self.nb_bobines_impose is not None
            or self.packaging_nb_etiq_par_bobine is not None
        ):
            raise ValueError(
                "Modes IMPOSE mutuellement exclusifs : nb_etiq_impose ne "
                "peut pas être combiné avec nb_bobines_impose / packaging."
            )
        if (
            self.packaging_nb_etiq_par_bobine is not None
            and self.nb_bobines_impose is None
        ):
            raise ValueError(
                "Mode packaging incomplet : packaging_nb_etiq_par_bobine "
                "fourni sans nb_bobines_impose. Les deux sont requis ensemble."
            )
        return self


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
    nb_bobines_total: int  # production RÉELLE (multiple de n_laize)
    quantite_totale_etiq: int
    surprod_etiq: int
    q_ajustee: int | None
    # Coût rebobinage (None si machine/tarifs absents — lecture seule).
    cout_total_eur: Decimal | None
    cout_machine_eur: Decimal | None
    cout_mandrins_eur: Decimal | None
    mode_mandrins_optimal: Literal["pre_coupe", "decoupe_interne"] | None
    # --- Extension modes IMPOSE nb_bobines + packaging ---
    # Renseigné UNIQUEMENT pour ces modes — sinon valeurs neutres.
    nb_bobines_demande: int | None = None
    surplus_bobines: int = 0
    surplus_etiq: int = 0
    # 3 options Q (None si mode non concerné par la décision surplus).
    q_si_facture: int | None = None
    q_si_stock: int | None = None
    q_si_reduire: int | None = None


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
    # --- Extension modes IMPOSE nb_bobines + packaging ---
    # `impose_type` distingue les 3 modes IMPOSE. None = scénario A/B/C non
    # IMPOSE (pas de demande client). `nb_bobines_demande` rappelle le
    # quoi-demandé par le client (vs nb_bobines_total = production réelle).
    # `decision_surplus` trace le choix du commercial (alimente la Q côté
    # cost_engine lecture seule). `surplus_bobines` snapshot du diff.
    impose_type: Literal["nb_etiq", "nb_bobines", "packaging"] | None = None
    nb_bobines_demande: int | None = Field(default=None, ge=1)
    surplus_bobines: int | None = Field(default=None, ge=0)
    decision_surplus: Literal["facture", "stock", "reduire"] | None = None

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
    # Extension modes IMPOSE nb_bobines + packaging — mêmes champs qu'en In.
    impose_type: Literal["nb_etiq", "nb_bobines", "packaging"] | None = None
    nb_bobines_demande: int | None = None
    surplus_bobines: int | None = None
    decision_surplus: Literal["facture", "stock", "reduire"] | None = None
