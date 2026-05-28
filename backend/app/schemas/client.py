from datetime import date

from pydantic import BaseModel, ConfigDict, Field


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

    # Sprint 16 — profil rebobinage client (9 colonnes additives, cf.
    # migration `s3h5c7d9f4e1`). Tous optionnels au POST/GET : les 6
    # nullable (Integer/String) gardent None par défaut, les 3 Boolean
    # prennent False (cohérent avec `default=False` côté ORM + server_default).
    diametre_mandrin_mm: int | None = None
    diametre_max_bobine_mm: int | None = None
    sens_enroulement: int | None = Field(default=None, ge=0, le=9)
    nb_etiq_par_bobine_fixe: int | None = Field(default=None, ge=1)
    marquage_bobine_requis: bool = False
    marquage_bobine_format: str | None = None
    mandrin_fourni_par_client: bool = False
    film_protection_requis: bool = False
    conditionnement_souhaite: str | None = None


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

    # Sprint 16 — profil rebobinage (partial update : tous None par
    # défaut, seuls les champs effectivement transmis sont écrits via
    # `exclude_unset=True` côté CRUD).
    diametre_mandrin_mm: int | None = None
    diametre_max_bobine_mm: int | None = None
    sens_enroulement: int | None = Field(default=None, ge=0, le=9)
    nb_etiq_par_bobine_fixe: int | None = Field(default=None, ge=1)
    marquage_bobine_requis: bool | None = None
    marquage_bobine_format: str | None = None
    mandrin_fourni_par_client: bool | None = None
    film_protection_requis: bool | None = None
    conditionnement_souhaite: str | None = None
