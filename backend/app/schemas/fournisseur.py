from pydantic import BaseModel, ConfigDict


class FournisseurBase(BaseModel):
    raison_sociale: str
    categorie: str | None = None
    contact: str | None = None
    email: str | None = None
    tel: str | None = None
    conditions_paiement: str | None = None
    delai_livraison_j: int | None = None


class FournisseurRead(FournisseurBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class FournisseurCreate(FournisseurBase):
    """Body POST : raison_sociale obligatoire."""


class FournisseurUpdate(BaseModel):
    """Body PUT : tous les champs optionnels (partial update)."""

    raison_sociale: str | None = None
    categorie: str | None = None
    contact: str | None = None
    email: str | None = None
    tel: str | None = None
    conditions_paiement: str | None = None
    delai_livraison_j: int | None = None
