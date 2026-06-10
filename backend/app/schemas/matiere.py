"""Schémas Pydantic — Matiere (catalogue matières Sprint 13 Lot S13.B).

Exposé via GET /api/matieres pour le sélecteur du formulaire /optimisation
(auto-fill épaisseur + transparence).
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MatiereEpaisseurPatch(BaseModel):
    """Lot E — mise à jour de l'épaisseur réelle d'une matière (µm).

    Permet de renseigner `epaisseur_microns` sur les matières qui l'avaient à
    NULL (le fallback 150 µm n'est qu'un pis-aller). `None` autorisé pour
    re-vider explicitement le champ."""

    model_config = ConfigDict(extra="forbid")

    epaisseur_microns: int | None = Field(None, ge=1, le=2000)


class MatiereOut(BaseModel):
    """Matière scopée tenant, telle qu'elle apparaît dans la liste API."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    code: str
    libelle: str
    categorie: str | None = None
    sous_type: str | None = None
    grammage_gm2: int | None = None
    epaisseur_microns: int | None = None
    est_transparent: bool
    opacite_pct: Decimal | None = None
    certifications_sanitaires: list[str] | None = None
    certifications_env: list[str] | None = None
    adhesifs_compatibles: list[str] | None = None
    actif: bool
