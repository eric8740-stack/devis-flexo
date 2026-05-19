"""Schémas Pydantic — CRUD /api/porte-cliches refondu (Brief #30).

Refonte métier suite Brief #29 incorrect : le modèle PorteCliche est
désormais (machine_id × cylindre_id × quantite) — cf
`app/models/porte_cliche.py` et migration h7d2e6f4a9c3.

`quantite` par défaut applicatif = `machine.nb_groupes_couleurs` (8
fallback si NULL). La validation FK + scope tenant est faite côté router.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PorteClicheCreate(BaseModel):
    """Body POST /api/porte-cliches."""

    model_config = ConfigDict(extra="forbid")

    machine_id: int
    cylindre_id: int
    # Si None, le router pose la default = machine.nb_groupes_couleurs.
    quantite: int | None = Field(None, ge=0, le=99)
    notes: str | None = Field(None, max_length=1000)
    actif: bool = True


class PorteClicheUpdate(BaseModel):
    """Body PATCH /api/porte-cliches/{id} — champs partiels.

    On NE permet PAS de modifier machine_id ou cylindre_id après création :
    ce sont les attributs identifiants du PC. Pour changer de couple,
    créer un nouveau PC et désactiver l'ancien.
    """

    model_config = ConfigDict(extra="forbid")

    quantite: int | None = Field(None, ge=0, le=99)
    notes: str | None = Field(None, max_length=1000)
    actif: bool | None = None


class PorteClicheRead(BaseModel):
    """Détail GET /api/porte-cliches/{id} + retour POST/PATCH.

    Inclut les `_nom` / `_nb_dents` joints pour l'UI (évite un GET en
    plus pour résoudre les FK).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    machine_nom: str
    machine_nb_couleurs: int | None
    cylindre_id: int
    cylindre_nb_dents: int
    cylindre_developpe_mm: str  # Decimal sérialisé en str pour le JSON
    quantite: int
    notes: str | None
    actif: bool
    created_at: datetime
    updated_at: datetime
