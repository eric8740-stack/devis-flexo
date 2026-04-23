from datetime import date

from pydantic import BaseModel, ConfigDict


class ClientBase(BaseModel):
    """Champs communs à Read / Create / Update."""

    raison_sociale: str
    siret: str | None = None
    adresse_fact: str | None = None
    cp_fact: str | None = None
    ville_fact: str | None = None
    contact: str | None = None
    email: str | None = None
    tel: str | None = None
    segment: str | None = None
    date_creation: date | None = None


class ClientRead(ClientBase):
    """Renvoyé par l'API : inclut l'id."""

    model_config = ConfigDict(from_attributes=True)
    id: int


class ClientCreate(ClientBase):
    """Body POST : raison_sociale obligatoire (héritée de Base), id auto."""


class ClientUpdate(BaseModel):
    """Body PUT : tous les champs optionnels (partial update via exclude_unset).

    On hérite de BaseModel directement (pas de ClientBase) pour rendre
    raison_sociale optionnelle aussi — utile pour un PATCH-style update.
    """

    raison_sociale: str | None = None
    siret: str | None = None
    adresse_fact: str | None = None
    cp_fact: str | None = None
    ville_fact: str | None = None
    contact: str | None = None
    email: str | None = None
    tel: str | None = None
    segment: str | None = None
    date_creation: date | None = None
