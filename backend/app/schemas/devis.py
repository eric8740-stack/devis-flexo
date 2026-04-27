"""Schémas Pydantic pour le moteur de calcul de devis (Sprint 3).

`DevisInput` est ce que le deviseur saisit ; `DevisOutput` est la réponse
détaillée du moteur — 7 postes nommés + cout_revient + prix_vente_ht +
détail (durées, surface) pour traçabilité en démo.
"""
from pydantic import BaseModel, ConfigDict, Field


class PartenaireSTForfait(BaseModel):
    """Forfait saisi à la volée pour un partenaire ST.

    Le tarif n'est PAS stocké en base car les ST négocient au cas par cas
    (laminage, dorure, numérique...). Le deviseur saisit le montant
    négocié pour le devis courant.
    """

    partenaire_st_id: int = Field(gt=0)
    montant_eur: float = Field(ge=0)


class DevisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ml: float = Field(gt=0, description="Longueur du tirage en mètres linéaires")
    largeur_bande_m: float = Field(
        gt=0, le=2.0, description="Largeur de bande utilisée (m)"
    )
    nb_couleurs: int = Field(ge=1, le=12)
    etiq_total: int = Field(
        gt=0, description="Nombre total d'étiquettes (sert aux opérations facturées à l'unité ou au millier)"
    )

    machine_id: int = Field(gt=0)
    complexe_id: int = Field(gt=0)

    operations_finition_ids: list[int] = Field(default_factory=list)
    partenaires_st: list[PartenaireSTForfait] = Field(default_factory=list)

    outillage_eur: float = Field(default=0.0, ge=0)

    # Si null, on prend pct_marge_defaut depuis entreprise.
    pct_marge_override: float | None = Field(default=None, ge=0, le=2.0)


class DevisOutput(BaseModel):
    """Sortie détaillée du moteur — 7 postes + total + détail traçable."""

    # 7 postes
    p1_matiere_eur: float
    p2_encres_eur: float
    p3_outillage_eur: float
    p4_roulage_eur: float
    p5_chutes_eur: float
    p6_finition_eur: float
    p7_frais_gx_eur: float

    # Totaux
    cout_revient_eur: float
    pct_marge_appliquee: float
    prix_vente_ht_eur: float

    # Détail (utile pour démo + débogage)
    surface_m2: float
    duree_calage_h: float
    duree_roulage_h: float
    duree_finition_h: float
    cout_horaire_structure_eur: float
