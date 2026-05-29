"""Schémas Pydantic — onglet Stratégique (Brief stratégique v2, Phase 1).

Config par entreprise : coûts/marges (singleton), changements (singleton),
roulage (collection par format). Montants exposés en float (convention JSON
du projet, cf. complexe.prix_m2_eur).
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModeRoulage = Literal["helicoidal", "alterne", "custom"]


# ---------------------------------------------------------------------------
# config_couts (singleton/tenant)
# ---------------------------------------------------------------------------
class ConfigCoutsBase(BaseModel):
    cout_exploitation_machine_eur_h: float = Field(ge=0)
    cout_operateur_eur_h: float = Field(ge=0)
    cout_energies_eur_h: float = Field(ge=0)
    cout_fixe_atelier_eur_mois: float = Field(ge=0)
    cout_fixe_maintenance_eur_mois: float = Field(ge=0)
    marge_standard_pct: float = Field(ge=0, le=100)
    buffer_rebut_pct: float = Field(ge=0, le=100)
    buffer_setup_pct: float = Field(ge=0, le=100)
    # Phase 2 Lot 4a — tarifs P1/P3/P4/P6 migrés depuis TarifPoste.
    # `surcout_forme_speciale_facteur` est un MULTIPLICATEUR direct
    # (1.30 = +30 %), pas un pourcentage — la valeur entre dans la formule
    # `cout_outil_base × facteur`. Borne haute 10.0 raisonnable (= +900 %).
    marge_confort_roulage_mm: int = Field(ge=0)
    cliche_prix_couleur_eur: float = Field(ge=0)
    outil_base_eur: float = Field(ge=0)
    outil_par_trace_eur: float = Field(ge=0)
    surcout_forme_speciale_facteur: float = Field(ge=1.0, le=10.0)
    calage_forfait_eur: float = Field(ge=0)
    finitions_prix_m2_eur: float = Field(ge=0)


class ConfigCoutsRead(ConfigCoutsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class ConfigCoutsUpdate(BaseModel):
    """PUT partiel (exclude_unset) — tous les champs optionnels."""

    cout_exploitation_machine_eur_h: float | None = Field(default=None, ge=0)
    cout_operateur_eur_h: float | None = Field(default=None, ge=0)
    cout_energies_eur_h: float | None = Field(default=None, ge=0)
    cout_fixe_atelier_eur_mois: float | None = Field(default=None, ge=0)
    cout_fixe_maintenance_eur_mois: float | None = Field(default=None, ge=0)
    marge_standard_pct: float | None = Field(default=None, ge=0, le=100)
    buffer_rebut_pct: float | None = Field(default=None, ge=0, le=100)
    buffer_setup_pct: float | None = Field(default=None, ge=0, le=100)
    # Phase 2 Lot 4a
    marge_confort_roulage_mm: int | None = Field(default=None, ge=0)
    cliche_prix_couleur_eur: float | None = Field(default=None, ge=0)
    outil_base_eur: float | None = Field(default=None, ge=0)
    outil_par_trace_eur: float | None = Field(default=None, ge=0)
    surcout_forme_speciale_facteur: float | None = Field(
        default=None, ge=1.0, le=10.0
    )
    calage_forfait_eur: float | None = Field(default=None, ge=0)
    finitions_prix_m2_eur: float | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# config_changements (singleton/tenant)
# ---------------------------------------------------------------------------
class ConfigChangementsBase(BaseModel):
    changement_couleur_duree_min: int = Field(ge=0)
    changement_couleur_cout_eur: float = Field(ge=0)
    changement_format_duree_min: int = Field(ge=0)
    changement_format_cout_eur: float = Field(ge=0)
    nettoyage_duree_min: int = Field(ge=0)
    nettoyage_cout_eur: float = Field(ge=0)


class ConfigChangementsRead(ConfigChangementsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class ConfigChangementsUpdate(BaseModel):
    changement_couleur_duree_min: int | None = Field(default=None, ge=0)
    changement_couleur_cout_eur: float | None = Field(default=None, ge=0)
    changement_format_duree_min: int | None = Field(default=None, ge=0)
    changement_format_cout_eur: float | None = Field(default=None, ge=0)
    nettoyage_duree_min: int | None = Field(default=None, ge=0)
    nettoyage_cout_eur: float | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# config_roulage (collection/tenant, par format)
# ---------------------------------------------------------------------------
class ConfigRoulageBase(BaseModel):
    format_libelle: str = Field(min_length=1, max_length=50)
    debit_mm_s: int = Field(gt=0)
    mode_roulage: ModeRoulage = "helicoidal"
    rebut_pct: float = Field(ge=0, le=100)


class ConfigRoulageRead(ConfigRoulageBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_creation: datetime
    date_maj: datetime


class ConfigRoulageCreate(ConfigRoulageBase):
    pass


class ConfigRoulageUpdate(BaseModel):
    format_libelle: str | None = Field(default=None, min_length=1, max_length=50)
    debit_mm_s: int | None = Field(default=None, gt=0)
    mode_roulage: ModeRoulage | None = None
    rebut_pct: float | None = Field(default=None, ge=0, le=100)
