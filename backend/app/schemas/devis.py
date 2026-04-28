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

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.poste_result import PosteResult


class PartenaireSTForfait(BaseModel):
    """Forfait sous-traitance saisi à la volée par le deviseur.

    Pas de tarif persisté côté ST : ils négocient au cas par cas
    (laminage, dorure, numérique, dos carré...). Alimente P6 Finitions.
    """

    partenaire_st_id: int = Field(gt=0)
    montant_eur: Decimal = Field(ge=0)


class DevisInput(BaseModel):
    """Saisie deviseur — alimente les 7 calculateurs v2."""

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

    # --- Couleurs (P2 + P3) ---
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


class DevisOutput(BaseModel):
    """Sortie moteur — 7 postes + totaux HT."""

    postes: list[PosteResult] = Field(min_length=7, max_length=7)
    cout_revient_eur: Decimal = Field(ge=0)
    pct_marge_appliquee: Decimal = Field(ge=0)
    prix_vente_ht_eur: Decimal = Field(ge=0)
