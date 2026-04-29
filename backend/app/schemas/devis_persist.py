"""Schémas Pydantic — persistance Devis (Sprint 4 Lot 4b).

Distincts de `app/schemas/devis.py` (qui porte DevisInput/DevisOutput
du moteur cost_engine). Ici : DevisCreate / DevisUpdate / DevisListItem /
DevisDetail / DevisListResponse pour les endpoints CRUD /api/devis.

PK Integer (homogène projet) — divergence vs brief UUID assumée Lot 4a.
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DevisCreate(BaseModel):
    """Body POST /api/devis.

    payload_input et payload_output sont validés côté client (déjà passés
    par le moteur cost_engine via /api/cost/calculer). Stockés en JSON
    pour flexibilité MVP.
    """

    model_config = ConfigDict(extra="forbid")

    payload_input: dict
    payload_output: dict
    client_id: int | None = None
    statut: Literal["brouillon", "valide"] = "brouillon"
    # Mode matching : cylindre choisi parmi les 3 candidats (UI Lot 4d).
    cylindre_choisi_z: int | None = None
    cylindre_choisi_nb_etiq: int | None = None


class DevisUpdate(BaseModel):
    """Body PUT /api/devis/{id} — partial update via exclude_unset."""

    model_config = ConfigDict(extra="forbid")

    payload_input: dict | None = None
    payload_output: dict | None = None
    client_id: int | None = None
    statut: Literal["brouillon", "valide"] | None = None
    cylindre_choisi_z: int | None = None
    cylindre_choisi_nb_etiq: int | None = None


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


class DevisListResponse(BaseModel):
    """Pagination GET /api/devis."""

    items: list[DevisListItem]
    total: int
    page: int
    per_page: int
    pages: int
