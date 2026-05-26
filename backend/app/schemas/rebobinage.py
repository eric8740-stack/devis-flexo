"""Schémas Pydantic Rebobinage — Sprint 16 Lot C.

Contrat HTTP du router `/api/rebobinage/*` et `/api/devis/{id}/rebobinage`.
Mappage vers les dataclasses du moteur isolé `app.services.rebobinage`.

Convention projet :
  - `from_attributes=True` sur les schémas de lecture
  - `extra="forbid"` sur les Create/Input pour rejeter les payloads inconnus
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Mode rebobinage — aligné sur services.rebobinage.types.ModeRebobinage
ModeRebobinageIn = Literal["auto", "pre_coupe", "decoupe_interne"]


# ---------------------------------------------------------------------------
# Inputs du calcul rebobinage
# ---------------------------------------------------------------------------


class SpecLotIn(BaseModel):
    """Caractéristiques du lot à rebobiner."""

    model_config = ConfigDict(extra="forbid")

    nb_etiquettes_total: int = Field(gt=0)
    intervalle_developpe_mm: Decimal = Field(gt=0)
    epaisseur_matiere_mm: Decimal = Field(gt=0)


class ProfilClientIn(BaseModel):
    """Contraintes client (passées en runtime — extension `client` reportée
    à un commit ultérieur, cf. note migration `q1f3a5d7e9c2`)."""

    model_config = ConfigDict(extra="forbid")

    diametre_mandrin_mm: int = Field(gt=0)
    diametre_max_bobine_mm: int = Field(gt=0)
    nb_etiq_par_bobine_fixe: int | None = Field(None, gt=0)


class TarifsMandrinsIn(BaseModel):
    """Tarifs mandrins runtime (non persistés à ce stade)."""

    model_config = ConfigDict(extra="forbid")

    prix_pre_coupe_par_mandrin_eur: Decimal = Field(ge=0)
    cout_decoupe_interne_par_mandrin_eur: Decimal = Field(ge=0)
    cout_fixe_decoupe_interne_eur: Decimal = Field(default=Decimal("0"), ge=0)


class RebobinageCalculerRequest(BaseModel):
    """Body POST /api/rebobinage/calculer et POST /api/devis/{id}/rebobinage.

    `machine_rebobineuse_id` : ref FK vers `machine_rebobineuse` du tenant
    courant. Le router charge la machine et en extrait vitesse / coût
    horaire / temps changement bobine.

    `mode` + `motif_force` : choix opérateur. Le moteur lève une erreur
    si mode forcé ≠ optimal sans motif (cf. Lot B `arbitrage_mandrins`).
    """

    model_config = ConfigDict(extra="forbid")

    spec_lot: SpecLotIn
    profil_client: ProfilClientIn
    machine_rebobineuse_id: int = Field(gt=0)
    tarifs_mandrins: TarifsMandrinsIn
    mode: ModeRebobinageIn = "auto"
    motif_force: str | None = None


# ---------------------------------------------------------------------------
# Sorties du moteur (sérialisation HTTP)
# ---------------------------------------------------------------------------


class ResultatBobinesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nb_etiq_par_bobine: int
    nb_bobines: int
    bobine_partielle: bool
    nb_etiq_derniere_bobine: int
    longueur_totale_m: Decimal


class ResultatTempsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    temps_roulage_min: Decimal
    temps_changements_min: Decimal
    temps_total_min: Decimal
    cout_machine_eur: Decimal


class ResultatArbitrageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mode_optimal: Literal["pre_coupe", "decoupe_interne"]
    cout_pre_coupe_total_eur: Decimal
    cout_decoupe_interne_total_eur: Decimal
    ecart_pct: Decimal
    mode_applique: Literal["pre_coupe", "decoupe_interne"]
    motif_force: str | None


class ResultatRebobinageOut(BaseModel):
    """Réponse complète du moteur (preview ou apply)."""

    model_config = ConfigDict(from_attributes=True)

    bobines: ResultatBobinesOut
    temps: ResultatTempsOut
    arbitrage: ResultatArbitrageOut
    cout_mandrins_eur: Decimal
    cout_total_rebobinage_eur: Decimal
    # Snapshot ID de la machine rebobineuse utilisée (utile pour l'UI
    # qui veut afficher le nom de la machine sans rappeler /api/machines).
    machine_rebobineuse_id: int
