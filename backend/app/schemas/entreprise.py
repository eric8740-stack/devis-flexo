from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class EntrepriseRead(BaseModel):
    """Renvoyé par l'API : tous les champs de la table entreprise."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    raison_sociale: str
    siret: str
    adresse: str | None = None
    cp: str | None = None
    ville: str | None = None
    tel: str | None = None
    email: str | None = None
    pct_fg: float | None = None
    pct_marge_defaut: float | None = None
    heures_prod_presse_mois: int | None = None
    heures_prod_finition_mois: int | None = None

    # PR #9.1 — paramètres BAT (Bon À Tirer)
    chute_laterale_min_mm: Decimal
    palier_laize_papier_mm: int
    refilage_systematique: bool
    marge_liner_mm: Decimal


class EntrepriseUpdate(BaseModel):
    """Body PUT : raison_sociale obligatoire, autres champs optionnels.

    Les champs non fournis ne sont PAS modifiés (partial update via
    exclude_unset côté CRUD).
    """

    raison_sociale: str
    siret: str | None = None
    adresse: str | None = None
    cp: str | None = None
    ville: str | None = None
    tel: str | None = None
    email: str | None = None
    pct_fg: float | None = None
    pct_marge_defaut: float | None = None
    heures_prod_presse_mois: int | None = None
    heures_prod_finition_mois: int | None = None

    # PR #9.1 — paramètres BAT, partial update donc tous optionnels.
    # Bornes métier raisonnables pour éviter les saisies aberrantes.
    chute_laterale_min_mm: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("50")
    )
    palier_laize_papier_mm: int | None = Field(default=None, ge=1, le=100)
    refilage_systematique: bool | None = None
    marge_liner_mm: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("50")
    )
