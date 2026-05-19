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
    sens_enroulement: int = Field(ge=1, le=8)
    quantite: int = Field(ge=1)
    matiere_id: int

    # Optionnels : snapshot des résultats moteur pour PDF / historique.
    intervalle_dev_reel_mm: Decimal | None = None
    intervalle_laize_reel_mm: Decimal | None = None
    largeur_plaque_mm: Decimal | None = None
    score_optim: float | None = None
    cout_lot_ht_eur: Decimal | None = None


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
    ht_total_eur: Decimal
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
    ht_total_eur: Decimal
    # Brief #32 — réduction commerciale (default 0, voir CRUD).
    reduction_pct: Decimal = Decimal(0)
    # Sprint 13 avenant — lots de production (liste vide si devis legacy
    # mono-config).
    lots_production: list[LotProductionRead] = Field(default_factory=list)


class DevisListResponse(BaseModel):
    """Pagination GET /api/devis."""

    items: list[DevisListItem]
    total: int
    page: int
    per_page: int
    pages: int
