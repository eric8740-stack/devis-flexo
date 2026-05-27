"""CRUD onglet Stratégique (Brief stratégique v2, Phase 1).

Singletons (couts/changements) : get-or-create avec valeurs par défaut
template du modèle, puis update partiel. Roulage : collection classique
scopée entreprise_id.
"""
from sqlalchemy.orm import Session

from app.models import ConfigChangements, ConfigCouts, ConfigRoulage
from app.schemas.config_strategique import (
    ConfigChangementsUpdate,
    ConfigCoutsUpdate,
    ConfigRoulageCreate,
    ConfigRoulageUpdate,
)


# --- config_couts (singleton) ---------------------------------------------
def get_or_create_couts(db: Session, entreprise_id: int) -> ConfigCouts:
    """Retourne la config coûts du tenant ; la crée (defaults template) si
    absente — GET idempotent côté onglet Stratégique."""
    cfg = (
        db.query(ConfigCouts).filter_by(entreprise_id=entreprise_id).first()
    )
    if cfg is None:
        cfg = ConfigCouts(entreprise_id=entreprise_id)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_couts(
    db: Session, entreprise_id: int, data: ConfigCoutsUpdate
) -> ConfigCouts:
    cfg = get_or_create_couts(db, entreprise_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cfg, field, value)
    db.commit()
    db.refresh(cfg)
    return cfg


# --- config_changements (singleton) ---------------------------------------
def get_or_create_changements(
    db: Session, entreprise_id: int
) -> ConfigChangements:
    cfg = (
        db.query(ConfigChangements)
        .filter_by(entreprise_id=entreprise_id)
        .first()
    )
    if cfg is None:
        cfg = ConfigChangements(entreprise_id=entreprise_id)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_changements(
    db: Session, entreprise_id: int, data: ConfigChangementsUpdate
) -> ConfigChangements:
    cfg = get_or_create_changements(db, entreprise_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cfg, field, value)
    db.commit()
    db.refresh(cfg)
    return cfg


# --- config_roulage (collection) ------------------------------------------
def list_roulage(db: Session, entreprise_id: int) -> list[ConfigRoulage]:
    return (
        db.query(ConfigRoulage)
        .filter_by(entreprise_id=entreprise_id)
        .order_by(ConfigRoulage.id)
        .all()
    )


def create_roulage(
    db: Session, data: ConfigRoulageCreate, entreprise_id: int
) -> ConfigRoulage:
    item = ConfigRoulage(entreprise_id=entreprise_id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_roulage(
    db: Session, item: ConfigRoulage, data: ConfigRoulageUpdate
) -> ConfigRoulage:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item
