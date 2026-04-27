from pydantic import BaseModel, ConfigDict


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
    # Paramètres calcul S3
    taux_chutes_defaut: float | None = None
    ratio_encre_m2_couleur: float | None = None
    heures_productives_mensuelles: int | None = None


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
    taux_chutes_defaut: float | None = None
    ratio_encre_m2_couleur: float | None = None
    heures_productives_mensuelles: int | None = None
