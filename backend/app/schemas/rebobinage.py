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
# Multi-lots (bug #6 étape 6.2a) — 1 Ø par lot, épaisseur réelle + paroi
# ---------------------------------------------------------------------------


class LotRebobinageIn(BaseModel):
    """Un lot à rebobiner. L'épaisseur effective et le Ø de départ sont
    résolus BACKEND (matière du lot + paroi mandrin), pas envoyés figés.

    - `matiere_id` (optionnel) : on lit `matiere.epaisseur_microns` du lot
      (scopé tenant). Si absent/NULL → on retombe sur `epaisseur_saisie_um`.
    - `epaisseur_saisie_um` (optionnel) : valeur opérateur, utilisée si la
      matière ne porte pas d'épaisseur. Ultime fallback backend = 150 µm.
    - `paroi_override_mm` (optionnel) : override de la paroi mandrin du
      `parametre_mandrin` pour ce lot.
    """

    model_config = ConfigDict(extra="forbid")

    nb_etiquettes_total: int = Field(gt=0)
    intervalle_developpe_mm: Decimal = Field(gt=0)
    diametre_mandrin_mm: int = Field(gt=0)
    diametre_max_bobine_mm: int = Field(gt=0)
    nb_etiq_par_bobine_fixe: int | None = Field(None, gt=0)
    matiere_id: int | None = Field(None, gt=0)
    epaisseur_saisie_um: Decimal | None = Field(None, gt=0)
    paroi_override_mm: int | None = Field(None, ge=0)


class RebobinageMultilotsRequest(BaseModel):
    """Body POST /api/rebobinage/calculer-multilots.

    Machine, tarifs et mode sont communs à tous les lots (1 rebobineuse,
    1 grille tarifaire, 1 mode opérateur). Chaque lot porte ses propres
    nb étiquettes / format / matière / mandrin → 1 Ø par lot.
    """

    model_config = ConfigDict(extra="forbid")

    lots: list[LotRebobinageIn] = Field(min_length=1)
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


# ---------------------------------------------------------------------------
# Sortie multi-lots (bug #6 étape 6.2a) — 1 résultat par lot
# ---------------------------------------------------------------------------


class LotRebobinageOut(BaseModel):
    """Résultat d'un lot : valeurs RÉSOLUES (transparence) + rebobinage.

    `epaisseur_source` documente d'où vient l'épaisseur retenue
    ("matiere" / "saisie" / "fallback") ; `diametre_depart_mm` = Ø mandrin
    + 2 × paroi (valeur passée au calcul bobines) ; `diametre_bobine_mm` =
    Ø max de bobine atteint (contrainte client = bobine pleine).
    """

    model_config = ConfigDict(from_attributes=True)

    # Échos résolus backend (à brancher au front en 6.2b).
    epaisseur_effective_um: float
    epaisseur_source: Literal["matiere", "saisie", "fallback"]
    mandrin_mm: int
    paroi_mm: int
    diametre_depart_mm: int
    diametre_bobine_mm: int

    # Résultat rebobinage du lot (nb bobines, temps, arbitrage, coûts).
    rebobinage: ResultatRebobinageOut


class RebobinageMultilotsResponse(BaseModel):
    """Réponse POST /api/rebobinage/calculer-multilots : 1 entrée par lot,
    dans l'ordre des lots envoyés."""

    model_config = ConfigDict(from_attributes=True)

    lots: list[LotRebobinageOut]


class RebobinageMultilotsApplyResponse(BaseModel):
    """Réponse POST /api/devis/{id}/rebobinage-multilots (apply persisté).

    Coût PAR LOT (`lots[].rebobinage.cout_total_rebobinage_eur`) + agrégat
    devis (`cout_total_rebobinage_eur` = somme des lots). Ligne additive :
    n'altère JAMAIS `ht_total_eur` (cost_engine sacré)."""

    model_config = ConfigDict(from_attributes=True)

    machine_rebobineuse_id: int
    nb_lots: int
    cout_total_rebobinage_eur: Decimal
    cout_mandrins_eur: Decimal
    lots: list[LotRebobinageOut]


# ---------------------------------------------------------------------------
# Liste des rebobineuses du tenant (sélecteur UI)
# ---------------------------------------------------------------------------


class MachineRebobineuseListItem(BaseModel):
    """Item retourné par GET /api/machines-rebobineuses.

    Champs minimaux pour alimenter un sélecteur côté UI — pas de coût
    horaire ni détails techniques (récupérables via /api/machines-
    rebobineuses/{id} si on l'ajoute plus tard).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    marque: str | None
    modele: str | None
    laize_max_mm: Decimal
    diametre_max_mm: int
    actif: bool
