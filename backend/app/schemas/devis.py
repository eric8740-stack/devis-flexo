"""Schémas Pydantic du moteur de calcul de devis v2 (Sprint 3 Lot 3c+).

Le moteur Lot 2 a été supprimé en bloc (bascule v1→v2) ; les calculateurs
v2 sont implémentés en Lot 3d sous `app/services/postes/poste_X_xxx.py`.

`DevisInput` couvre les 7 postes du modèle V2 raffiné :
  P1 Matière       — laize_utile_mm + ml_total + complexe_id (grammage + prix_m2)
  P2 Encres        — nb_couleurs_par_type (clé = tarif_encre.type_encre)
  P3 Outillage     — dérivé de nb_couleurs_par_type (somme des couleurs)
  P4 Calage        — forfait fixe (tarif_poste calage_forfait)
  P5 Roulage       — ml_total / vitesse_moyenne_m_h (machine) × roulage_prix_horaire
  P6 Finitions     — surface_utile + forfaits_st saisis à la volée
  P7 MO            — heures_dossier × mo_prix_horaire (override possible)

`DevisOutput` retourne les 7 postes en liste (itération front simple) +
les 3 totaux du HT seul. TVA / total TTC viennent en S4 quand on aura
le devis persisté avec un client.
"""
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.poste_result import PosteResult


ModeCalcul = Literal["manuel", "matching"]


class PartenaireSTForfait(BaseModel):
    """Forfait sous-traitance saisi à la volée par le deviseur.

    Pas de tarif persisté côté ST : ils négocient au cas par cas
    (laminage, dorure, numérique, dos carré...). Alimente P6 Finitions.
    """

    partenaire_st_id: int = Field(gt=0)
    montant_eur: Decimal = Field(ge=0)


class DevisInput(BaseModel):
    """Saisie deviseur — alimente les 7 calculateurs v2.

    Sprint 5 Lot 5b : 8 champs « format / outillage » ajoutés avec defaults
    rétrocompatibles (Option B validée Eric). Les payloads existants (S3 V1-V5)
    fonctionnent sans les passer, les defaults sont appliqués. Les calculateurs
    P3 et le calcul `prix_au_mille_eur` consommeront ces champs en Lot 5c.
    """

    model_config = ConfigDict(extra="forbid")

    # --- Matière / format (P1) ---
    complexe_id: int = Field(
        gt=0,
        description="Référence complexe seedé — dérive grammage_g_m2 et prix_m2_eur",
    )
    laize_utile_mm: int = Field(
        gt=0,
        description="Laize utile en mm (P1, P5, P6). marge_confort_roulage_mm "
        "ajoutée par le calculateur P1 via tarif_poste.",
    )
    ml_total: int = Field(gt=0, description="Métrage total commandé en mètres")

    # --- Couleurs (P2 + P3a) ---
    nb_couleurs_par_type: dict[str, int] = Field(
        default_factory=dict,
        description="Clés = tarif_encre.type_encre. Ex : {'process_cmj': 4, "
        "'pantone': 2}. Validation des clés faite côté calculateur.",
    )

    # --- Machine (P5) ---
    machine_id: int = Field(
        gt=0,
        description="Machine de production — détermine vitesse_moyenne_m_h",
    )

    # --- Format étiquette + outillage découpe (P3b + prix_au_mille — Sprint 5) ---
    format_etiquette_largeur_mm: int = Field(
        default=60,
        gt=0,
        description="Largeur unitaire de l'étiquette (mm). Default cas V1a.",
    )
    format_etiquette_hauteur_mm: int = Field(
        default=40,
        gt=0,
        description="Hauteur unitaire de l'étiquette (mm). Default cas V1a.",
    )
    nb_poses_largeur: int = Field(
        default=3,
        ge=1,
        description="Nombre d'étiquettes en largeur de laize. Default cas V1a.",
    )
    nb_poses_developpement: int = Field(
        default=1,
        ge=1,
        description="Nombre d'étiquettes dans le développement cylindre. Default cas V1a.",
    )
    forme_speciale: bool = Field(
        default=False,
        description="Forme non-rectangulaire — surcoût plaque +40 % si nouvel outil.",
    )
    outil_decoupe_existant: bool = Field(
        default=True,
        description="True (cas standard) → P3b = 0 €. False → calcul à la volée.",
    )
    outil_decoupe_id: int | None = Field(
        default=None,
        gt=0,
        description="Référence catalogue si outil existant identifié. None autorisé "
        "(cas outil existant générique non référencé). Sert à tracer dans details.",
    )
    nb_traces_complexite: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Nombre de tracés à découper. Utilisé seulement si nouvel outil. "
        "Coût base = 200 + nb_traces × 50.",
    )

    # --- Mode de calcul (Sprint 7 Note 11 vraie réalisation) ---
    mode_calcul: ModeCalcul = Field(
        default="manuel",
        description="'manuel' : utilisateur saisit intervalle_mm libre (rétrocompat "
        "Sprint 5 V1a/V1b). 'matching' : le moteur cherche les 3 couples (Z, "
        "nb_etiq_par_tour) optimaux dans la plage Z=51-144 × nb_etiq=1-40 "
        "(sortie multi-résultats DevisOutputMatching). Plage corrigée par tableau "
        "Excel Develop.xlsx Eric (28 ans flexo ICE).",
    )
    intervalle_mm: Decimal | None = Field(
        default=None,
        ge=Decimal("2.5"),
        le=Decimal("15"),
        description="Distance en mm entre 2 étiquettes consécutives (sens longitudinal). "
        "Pas de saisie 0.5. Utilisé seulement si mode_calcul='manuel'. "
        "Si None en mode manuel → default 3 mm appliqué par le moteur (préserve "
        "V1a EXACT). En mode 'matching', DOIT rester None (validateur cross-field).",
    )

    # --- Sous-traitance saisie à la volée (P6) ---
    forfaits_st: list[PartenaireSTForfait] = Field(default_factory=list)

    # --- Overrides optionnels ---
    heures_dossier_override: Decimal | None = Field(
        default=None,
        ge=0,
        description="P7 : si null, dérivé par le moteur "
        "(calage_forfait_h + ml/vitesse + finition estimée)",
    )
    pct_marge_override: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("2"),
        description="Si null, lit entreprise.pct_marge_defaut (curseur 4 presets)",
    )

    @model_validator(mode="after")
    def _check_intervalle_coherent_avec_mode(self) -> Self:
        """Sprint 7 Lot 7b — interdit intervalle_mm en mode matching.

        En mode 'matching', l'intervalle est CONSÉQUENCE du choix de cylindre
        magnétique (Z × 3.175 - format_h), pas une entrée. Permettre les deux
        en même temps serait sémantiquement incohérent.
        """
        if self.mode_calcul == "matching" and self.intervalle_mm is not None:
            raise ValueError(
                "intervalle_mm doit être None en mode 'matching' — "
                "le moteur le calcule à partir du cylindre optimal trouvé"
            )
        return self


class DevisOutput(BaseModel):
    """Sortie moteur — mode 'manuel' (Sprint 5 + Sprint 7 Lot 7b).

    7 postes + totaux HT + prix au mille calculé pour 1 cylindre théorique
    (l'utilisateur a saisi intervalle_mm, le moteur applique 3 mm si None).
    Discriminant `mode='manuel'` pour distinguer du DevisOutputMatching.
    """

    mode: Literal["manuel"] = "manuel"
    postes: list[PosteResult] = Field(min_length=7, max_length=7)
    cout_revient_eur: Decimal = Field(ge=0)
    pct_marge_appliquee: Decimal = Field(ge=0)
    prix_vente_ht_eur: Decimal = Field(ge=0)
    # Sprint 5 Lot 5c : prix au mille étiquettes (livrable commercial clé).
    # Calculé par l'orchestrateur à partir de format_h, intervalle (3 mm
    # default mode manuel ou saisi user), nb_poses_l × nb_poses_d et ml_total.
    prix_au_mille_eur: Decimal = Field(ge=0)


# ---------------------------------------------------------------------------
# Sprint 7 Lot 7c V2 — sortie multi-résultats pour mode 'matching'
# Formule corrigée (tableau Eric Develop.xlsx) :
#   pas_mm = (Z × 3.175) / nb_etiq_par_tour
#   intervalle_mm = pas_mm - format_h
# ---------------------------------------------------------------------------


class CandidatCylindreOutput(BaseModel):
    """Un candidat cylindre magnétique = 1 couple (Z, nb_etiq_par_tour).

    Le moteur retourne 1-3 candidats triés par intervalle croissant
    (= meilleur prix au mille en premier). Pour chaque cylindre physique
    (Z donné), on garde le couple (Z, nb_etiq) qui donne le meilleur
    intervalle (cf. Règle 8 brief Sprint 7 v2).

    Plages :
      Z              : 51 à 144 (vraie plage flexo ICE, abaque Develop.xlsx)
      nb_etiq_par_tour : 1 à 40 (limite haute du tableau Eric)
      intervalle_mm  : 2.5 à 15 (contrainte hauteur métier)
    """

    z: int = Field(ge=51, le=144, description="Nombre de dents du cylindre (1 dent = 3.175 mm)")
    nb_etiq_par_tour: int = Field(
        ge=1,
        le=40,
        description="Nombre d'étiquettes imprimées par tour de cylindre. "
        "circonférence = pas × nb_etiq.",
    )
    circonference_mm: Decimal = Field(gt=0, description="Z × 3.175 mm")
    pas_mm: Decimal = Field(
        gt=0,
        description="Pas de répétition = circonférence / nb_etiq_par_tour = "
        "format_h + intervalle.",
    )
    intervalle_mm: Decimal = Field(ge=Decimal("2.5"), le=Decimal("15"))
    nb_etiq_par_metre: int = Field(gt=0, description="floor(1000 / pas_mm)")

    # Devis calculé pour ce candidat (les 7 postes ne dépendent PAS du choix
    # de cylindre dans le moteur actuel — seul prix_au_mille varie via le
    # nb_etiq_total dérivé du pas. Donc HT identique entre candidats, mais
    # exposition complète conservée pour audit + évolution Sprint 8+).
    postes: list[PosteResult] = Field(min_length=7, max_length=7)
    cout_revient_eur: Decimal = Field(ge=0)
    pct_marge_appliquee: Decimal = Field(ge=0)
    prix_vente_ht_eur: Decimal = Field(ge=0)
    prix_au_mille_eur: Decimal = Field(ge=0)


class DevisOutputMatching(BaseModel):
    """Sortie moteur — mode 'matching' (Sprint 7 Lot 7c V2).

    1 à 3 cylindres candidats triés par intervalle croissant (= meilleur
    prix au mille en premier). Si moins de 3 compatibles avec les contraintes
    (effet banane + plage intervalle + laize machine), 2 ou 1 retournés.
    Si aucun → CostEngineError 422 levée par le moteur en amont (Lot 7d V2).

    Discriminant `mode='matching'` pour distinguer du DevisOutput Sprint 5.
    """

    mode: Literal["matching"] = "matching"
    candidats: list[CandidatCylindreOutput] = Field(min_length=1, max_length=3)
