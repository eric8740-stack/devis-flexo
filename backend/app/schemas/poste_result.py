from decimal import Decimal

from pydantic import BaseModel, Field


class PosteResult(BaseModel):
    """Résultat d'un poste de coût (1 à 7) — partagé par tous les calculateurs.

    `details` expose les valeurs intermédiaires utilisées par le calculateur
    (surface, durée, lookup tarif, ...) pour audit et démo. Volontairement
    typé large mais JSON-safe : pas de Decimal pour rester sérialisable
    sans surprise. `None` autorisé pour les références optionnelles
    (ex. `outil_decoupe_id` non identifié — Lot 5c). Les montants métier
    précis restent dans `montant_eur`.
    """

    poste_numero: int = Field(ge=1, le=7)
    libelle: str = Field(min_length=1, max_length=100)
    montant_eur: Decimal = Field(ge=0)
    details: dict[str, float | int | str | None] = Field(default_factory=dict)
