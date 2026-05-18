"""Dataclasses du moteur d'optimisation Sprint 13 Lot S13.D.

Séparation stricte domaine ↔ persistence : ces types ne référencent
AUCUN modèle SQLAlchemy. C'est l'API de la couche service.

Le router (S13.D.7) hydrate ces dataclasses depuis les modèles BDD
(MachineImprimerie, CylindreMagnetique, Bareme, etc.) avant d'appeler
le moteur. Avantages :
  - Les règles métier sont testables avec des données littérales
    (pas besoin de DB en test unitaire).
  - On peut faire évoluer les modèles SQLAlchemy sans casser le moteur.
  - Le moteur reste utilisable hors web (CLI, batch, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Entrées — données saisies / sélectionnées par l'utilisateur
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Format:
    """Format d'étiquette demandé (CdC § format_h × format_l).

    `rayon_angles_mm` : 0 = angles vifs, ∞ = courbe. Influe sur le
    confort de roulage (S13.D.4).
    `forme_courbe` : rond/ovale (booster confort à 1.15 indépendamment
    du rayon — CdC ligne 737).
    """

    hauteur_mm: float
    largeur_mm: float
    rayon_angles_mm: float = 2.0  # standard
    forme_courbe: bool = False


@dataclass(frozen=True)
class Cylindre:
    """Cylindre magnétique candidat à la pose."""

    id: int
    developpe_mm: float


@dataclass(frozen=True)
class Machine:
    """Machine d'impression candidate."""

    id: int
    nom: str
    laize_utile_mm: float
    nb_groupes_couleurs: int
    nb_postes_decoupe: int = 1
    vitesse_pratique_m_min: int = 60
    cout_horaire_eur: float = 0.0
    # Modules présents : "UV", "hot_stamping", "retournement_laize", ...
    options: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OptionFabrication:
    """Option de fabrication sélectionnée par l'utilisateur sur le devis.

    Reflète une row de la table option_fabrication (Sprint 13.B) :
    coefs vitesse/gâche, modules requis, groupes couleurs consommés.
    """

    code: str
    libelle: str
    groupes_couleurs_requis: int = 0
    modules_speciaux_requis: list[str] = field(default_factory=list)
    coef_vitesse_impact: float = 1.0
    coef_gache_impact: float = 1.0
    ajoute_temps_calage_min: int = 0


@dataclass(frozen=True)
class ContrainteClient:
    """Contraintes imposées par la machine de pose du client final
    (CdC § 786).
    """

    # Plancher d'intervalle dev (cellule photoélectrique du client).
    # Si > intervalle_dev_min_imprimeur, c'est lui qui s'applique.
    intervalle_dev_min_mm: float = 0.0


@dataclass(frozen=True)
class OptimisationInput:
    """Tout ce dont le moteur a besoin pour calculer un top 3."""

    format: Format
    intervalle_dev_min_mm: float  # minimum imprimeur (paramètre entreprise)
    nb_couleurs_impression: int  # CMJN + Pantone + spot
    quantite: int
    matiere_est_transparente: bool = False  # déclenche spot detection
    options: list[OptionFabrication] = field(default_factory=list)
    cylindres: list[Cylindre] = field(default_factory=list)
    machines: list[Machine] = field(default_factory=list)
    bareme_echenillage: list[dict] = field(default_factory=list)
    bareme_effet_banane: list[dict] = field(default_factory=list)
    bareme_compensation: list[dict] = field(default_factory=list)
    bareme_confort_roulage: dict = field(default_factory=dict)
    contrainte_client: ContrainteClient = field(
        default_factory=ContrainteClient
    )
    # Sprint 13 avenant : forçage du nb poses laize. None = comportement
    # standard (max, max-1, max-2). Sinon, le moteur se bloque sur N poses
    # laize ; les candidats qui ne satisfont pas N * largeur ≤ laize_utile
    # sont skippés.
    nb_poses_laize_force: int | None = None


# ---------------------------------------------------------------------------
# Sorties — résultats du moteur (top 3 configurations)
# ---------------------------------------------------------------------------


@dataclass
class ConfigurationPose:
    """Une configuration candidate produite par le moteur.

    Mutable (vs frozen) car les règles ajoutent leurs coefficients
    progressivement avant le scoring final.
    """

    cylindre_id: int
    machine_id: int
    nb_poses_dev: int
    nb_poses_laize: int
    nb_poses_total: int
    intervalle_dev_reel_mm: float
    intervalle_laize_reel_mm: float
    # Effet banane : largeur de la plaque effective + Z mini requis
    largeur_plaque_mm: float
    z_mini_effet_banane: float

    # Coefficients par règle (multiplicatifs entre eux)
    coef_vitesse_echenillage: float = 1.0
    coef_gache_echenillage: float = 1.0
    coef_confort_rayon: float = 1.0
    coef_quinconce: float = 1.0
    coef_consolidation: float = 1.0  # bonus compensation laize/dev
    coef_vitesse_options: float = 1.0  # produit des options
    coef_gache_options: float = 1.0

    qualite_echenillage: str = "parfait"  # parfait/bien/complique/mauvais/critique
    consolidation_atteinte: bool = False
    intervalle_laize_souhaitable_mm: float | None = None
    disposition_poses: str = "alignee"  # ou "quinconce"

    # Score [0..100] post-règles (calculé par l'orchestrateur)
    score: float = 0.0

    # PR #9.1 — dédoublonnage : agrège les machines équivalentes (mêmes
    # cylindre/poses/intervalles, différentes machines). Initialisé à
    # [machine_id] par le moteur, fusionné par `_dedoublonner_configs`.
    machines_compatibles: list[int] = field(default_factory=list)

    @property
    def coef_vitesse_final(self) -> float:
        """Coefficient vitesse cumulé (CdC § 758)."""
        return (
            self.coef_vitesse_echenillage
            * self.coef_consolidation
            * self.coef_confort_rayon
            * self.coef_quinconce
            * self.coef_vitesse_options
        )

    @property
    def coef_gache_final(self) -> float:
        """Coefficient gâche cumulé (CdC § 1138)."""
        return self.coef_gache_echenillage * self.coef_gache_options


@dataclass
class OptimisationOutput:
    """Réponse du moteur : top N (≤ 3) configurations + métadonnées.

    `nb_candidats` < 3 → message explicatif demandé par CdC § 658
    ("pas de triche").
    """

    configurations: list[ConfigurationPose]
    nb_candidats: int
    message_filtrage: str | None = None
    intervalle_dev_min_applique_mm: float = 0.0
    message_contrainte_client: str | None = None


# ---------------------------------------------------------------------------
# Filtre dur — résultat d'un filtre type effet_banane / capacité couleurs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FiltreResult:
    """Résultat d'un filtre dur (capacité couleurs, effet banane, ...).

    `ok=False` → la combinaison testée est éliminée, et `raison`
    explique pourquoi (utilisé pour générer le message_filtrage final
    et pour l'analytique).
    """

    ok: bool
    raison: str | None = None
    message: str | None = None
