"""Schémas Pydantic — optimisation Sprint 13 Lot S13.D.7b.

POST /api/optimisation/calculer : reçoit le contexte devis + sélection
matière/options, hydrate depuis la BDD (cylindres + machines + barèmes
du tenant) puis appelle optimiser_pose(). Renvoie top 3 + metadata.

extra='forbid' partout pour rejeter les champs accessoires.
"""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.matiere import MatiereOut


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class OptimisationFormat(BaseModel):
    """Format d'étiquette demandé."""

    model_config = ConfigDict(extra="forbid")

    hauteur_mm: float = Field(..., gt=0, le=2000)
    largeur_mm: float = Field(..., gt=0, le=2000)
    rayon_angles_mm: float = Field(2.0, ge=0, le=999)
    forme_courbe: bool = False


class OptimisationContrainteClient(BaseModel):
    """Contraintes machine de pose client (optionnel)."""

    model_config = ConfigDict(extra="forbid")

    intervalle_dev_min_mm: float = Field(0.0, ge=0, le=20)


class OptimisationCalculerRequest(BaseModel):
    """Body de POST /api/optimisation/calculer.

    Les cylindres + machines + barèmes sont hydratés côté serveur depuis
    le tenant (pas d'ID à passer). Seules les sélections du commercial
    transitent : format, options, contraintes.
    """

    model_config = ConfigDict(extra="forbid")

    format: OptimisationFormat
    intervalle_dev_min_mm: float = Field(
        2.0, ge=0, le=20, description="Plancher imprimeur (typique 2 mm)"
    )
    nb_couleurs_impression: int = Field(
        ..., ge=0, le=16, description="CMJN + Pantone + spot"
    )
    quantite: int = Field(..., gt=0, le=100_000_000)
    matiere_est_transparente: bool = False
    options_codes: list[str] = Field(
        default_factory=list,
        description="Codes options du tenant (table option_fabrication)",
    )
    contrainte_client: OptimisationContrainteClient = Field(
        default_factory=OptimisationContrainteClient
    )

    # PR #9.1 — paramètres BAT (volatile pour MVP, persistés sur devis en 9.3)
    mandrin_mm: int = Field(
        76,
        description="Diamètre mandrin (25/38/76/152 mm typiquement)",
        ge=10,
        le=500,
    )
    sens_enroulement: Literal["SE1", "SE2", "SE3", "SE4", "SE5", "SE6", "SE7", "SE8"] = Field(
        "SE1",
        description=(
            "Sens enroulement bobine fille (convention métier flexo 8 sens) : "
            "SE1-4 face extérieur (0°/180°/270°/90°), "
            "SE5-8 face intérieur (0°/180°/270°/90°)."
        ),
    )
    epaisseur_matiere_um: float = Field(
        150.0,
        ge=10,
        le=1000,
        description="Épaisseur totale matière (étiq + liner adhésif), µm",
    )

    # ---- Souveraineté commerciale (Règle 7) ---------------------------------
    # Matière FK obligatoire. Le moteur lit l'épaisseur + transparence depuis
    # la matière, surchargeables via `epaisseur_matiere_force_um` et
    # `matiere_est_transparente` (déjà existant ci-dessus).
    matiere_id: int | None = Field(
        None,
        description=(
            "FK matière du tenant. Optionnel pour rétro-compat (les anciens "
            "clients qui n'envoient pas matiere_id retombent sur le champ "
            "epaisseur_matiere_um direct). Recommandé en pratique."
        ),
    )
    epaisseur_matiere_force_um: int | None = Field(
        None,
        ge=10,
        le=1000,
        description=(
            "Si renseignée, surcharge l'épaisseur du catalogue matière. "
            "Motif obligatoire (>=10 caractères). Règle 7."
        ),
    )
    motif_forcage_epaisseur: str | None = Field(None, max_length=500)

    # Intervalle laize forçable (souveraineté). NULL = moteur libre de
    # choisir selon ses règles (palier suggérable / max 5 mm).
    intervalle_laize_force_mm: float | None = Field(
        None,
        ge=0,
        le=50,
        description="Force la valeur d'intervalle laize. Motif obligatoire.",
    )
    motif_forcage_intervalle_laize: str | None = Field(None, max_length=500)

    # Intervalle dev forçable (souveraineté — audit règle 7).
    intervalle_dev_force_mm: float | None = Field(
        None,
        ge=0,
        le=50,
        description="Force la valeur d'intervalle dev. Motif obligatoire.",
    )
    motif_forcage_intervalle_dev: str | None = Field(None, max_length=500)

    # Lacets bobine fille (marge liner siliconé de chaque côté de l'étiquette).
    # Par défaut symétrique = intervalle_laize_applique / 2. Le client peut
    # demander des lacets asymétriques (rebobinage particulier).
    lacets_asymetriques: bool = False
    lacet_droit_mm: float | None = Field(None, ge=0.5, le=50)
    lacet_gauche_mm: float | None = Field(None, ge=0.5, le=50)

    @model_validator(mode="after")
    def _valider_forcages_et_lacets(self) -> "OptimisationCalculerRequest":
        # Forçage intervalle laize → motif obligatoire ≥ 10 chars
        if self.intervalle_laize_force_mm is not None:
            motif = (self.motif_forcage_intervalle_laize or "").strip()
            if len(motif) < 10:
                raise ValueError(
                    "Forçage intervalle laize : motif obligatoire (10 caractères min)."
                )

        # Forçage intervalle dev → motif obligatoire ≥ 10 chars
        if self.intervalle_dev_force_mm is not None:
            motif = (self.motif_forcage_intervalle_dev or "").strip()
            if len(motif) < 10:
                raise ValueError(
                    "Forçage intervalle dev : motif obligatoire (10 caractères min)."
                )

        # Forçage épaisseur → motif obligatoire ≥ 10 chars
        if self.epaisseur_matiere_force_um is not None:
            motif = (self.motif_forcage_epaisseur or "").strip()
            if len(motif) < 10:
                raise ValueError(
                    "Forçage épaisseur matière : motif obligatoire (10 caractères min)."
                )

        # Lacets asymétriques → les deux valeurs obligatoires + min 0.5 mm
        if self.lacets_asymetriques:
            if self.lacet_droit_mm is None or self.lacet_gauche_mm is None:
                raise ValueError(
                    "Lacets asymétriques : lacet_droit_mm et lacet_gauche_mm obligatoires."
                )
        return self


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OptimisationConfigOut(BaseModel):
    """Une configuration candidate du top N."""

    model_config = ConfigDict(extra="forbid")

    cylindre_id: int
    machine_id: int
    nb_poses_dev: int
    nb_poses_laize: int
    nb_poses_total: int
    intervalle_dev_reel_mm: float
    intervalle_laize_reel_mm: float
    largeur_plaque_mm: float
    z_mini_effet_banane: float
    qualite_echenillage: str
    consolidation_atteinte: bool
    intervalle_laize_souhaitable_mm: float | None = None
    disposition_poses: str
    coef_vitesse_echenillage: float
    coef_gache_echenillage: float
    coef_confort_rayon: float
    coef_quinconce: float
    coef_consolidation: float
    coef_vitesse_options: float
    coef_gache_options: float
    coef_vitesse_final: float
    coef_gache_final: float
    score: float

    # PR #9.1 — enrichissements BAT (Bon À Tirer) calculés par le router à
    # partir des params tenant (chute, palier, marge_liner) et du payload
    # client (mandrin, sens enroulement, épaisseur matière).
    laize_plaque_mm: float
    laize_papier_mm: float
    chute_laterale_reelle_mm: float
    z_cylindre_mm: float
    # Nomenclature ICE : les imprimeurs désignent un cylindre par son
    # nombre de dents (1 dent = 3.175 mm). On expose les deux pour
    # afficher "104 dents (Z=330.2 mm)" dans l'UI.
    nb_dents_cylindre: int
    ml_total_m: float
    m2_consomme: float
    rendement_pct: float
    diametre_bobine_mm: int
    laize_liner_mm: float
    sens_enroulement: Literal["SE1", "SE2", "SE3", "SE4", "SE5", "SE6", "SE7", "SE8"]
    # Libellé officiel ICE à afficher dans le BAT et le formulaire.
    # Ex: "0° Extérieur droite avant". Calculé backend (rotation_se.py).
    sens_enroulement_libelle: str
    # Rotations à appliquer au A en VUE A (planche presse, sens machine) et
    # VUE C (bobine fille chez le client). Mapping officiel verrouillé
    # 18/05/2026 — paires ext/int partagent la même rotation.
    rotation_vue_a_deg: int
    rotation_vue_c_deg: int
    # Machines équivalentes (dédoublonnage). Au moins l'élément `machine_id`.
    machines_compatibles: list[int]
    # Noms machines équivalentes — facilité d'affichage UI (au lieu d'IDs).
    noms_machines_compatibles: list[str]

    # ---- Souveraineté commerciale (Règle 7) — écho des forçages ------------
    # Valeurs "recommandées par le moteur" vs "appliquées effectivement".
    # Le frontend les compare pour afficher l'écart le cas échéant.
    intervalle_laize_recommande_mm: float
    intervalle_laize_applique_mm: float
    forcage_intervalle_laize: bool
    motif_forcage_intervalle_laize: str | None = None

    intervalle_dev_recommande_mm: float
    intervalle_dev_applique_mm: float
    forcage_intervalle_dev: bool
    motif_forcage_intervalle_dev: str | None = None

    # Lacets bobine fille (calculés selon paramètres entrée).
    lacet_droit_mm: float
    lacet_gauche_mm: float
    lacets_asymetriques: bool

    # Matière sélectionnée + épaisseur appliquée (forcée ou catalogue).
    matiere: MatiereOut | None = None
    epaisseur_appliquee_um: int
    forcage_epaisseur: bool
    motif_forcage_epaisseur: str | None = None


class OptimisationCalculerResponse(BaseModel):
    """Top N (≤ 3) + métadonnées explicatives."""

    model_config = ConfigDict(extra="forbid")

    configurations: list[OptimisationConfigOut]
    nb_candidats: int
    message_filtrage: str | None = None
    intervalle_dev_min_applique_mm: float
    message_contrainte_client: str | None = None
    debug: dict[str, Any] | None = None


class OptionDisponiblePublic(BaseModel):
    """Option de fabrication réellement disponible pour le tenant courant
    (présente dans `option_fabrication`, scopée tenant ou catalogue global).

    Sert à peupler les checkboxes de la page d'optimisation : seules les
    options exposées ici sont garanties d'être acceptées par
    POST /api/optimisation/calculer.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    code: str
    libelle: str
    categorie: str | None = None
    coef_vitesse_impact: float
    coef_gache_impact: float
