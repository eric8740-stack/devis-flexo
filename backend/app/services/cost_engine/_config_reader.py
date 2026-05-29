"""Lecture centralisée des configs entreprise (Stratégique, Phase 1).

Centralise les requêtes `ConfigCouts` scopées `entreprise_id` pour les
calculateurs (P5, P7) et l'orchestrator (marge). Évite la duplication
de la même requête + erreur dans 3 endroits différents et garantit que
l'erreur explicite (config absente) est levée de façon uniforme.

Pas de cache : la session SQLAlchemy gère déjà l'identity map locale ;
les appels multiples sur la même session servent l'objet depuis le cache
de session.
"""
from sqlalchemy.orm import Session

from app.models import ConfigCouts
from app.services.cost_engine.errors import CostEngineError


def get_config_couts_or_raise(db: Session, entreprise_id: int) -> ConfigCouts:
    """Retourne la `ConfigCouts` du tenant ou lève `CostEngineError` si absente.

    Le scope strict `filter_by(entreprise_id=...)` est l'invariant multi-tenant
    sacré (cf. fix Phase 2 Lot 2 de `_resolve_pct_marge`) : aucune fuite
    cross-tenant possible.
    """
    config = (
        db.query(ConfigCouts)
        .filter_by(entreprise_id=entreprise_id)
        .first()
    )
    if config is None:
        raise CostEngineError(
            f"ConfigCouts introuvable pour entreprise_id={entreprise_id} "
            "— config Stratégique manquante. Initialise via "
            "/api/strategique/couts."
        )
    return config
