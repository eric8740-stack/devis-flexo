"""Helpers de scope multi-tenant — Sprint 12 Lot S12-C.

Factorise le pattern de filtrage par `entreprise_id` pour éviter de dupliquer
`query.filter(Model.entreprise_id == user.entreprise_id)` sur 50 endpoints.

Convention sécurité Sprint 12 :
- Une ressource d'une autre entreprise doit retourner 404 (et NON 403).
  → Pas de divulgation d'existence d'IDs hors scope (anti-enumeration).
- Le filtre se fait au niveau Query SQLAlchemy, pas au niveau Python post-fetch.
  → Pas de fuite mémoire / ORM.
"""
from __future__ import annotations

from typing import Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Query, Session

from app.models import User

T = TypeVar("T")


def scope_to_entreprise(
    query: Query, model_class: Type[T], user: User
) -> Query:
    """Filtre une query SQLAlchemy sur `entreprise_id == user.entreprise_id`.

    À utiliser sur tous les LIST/COUNT et toute query qui retourne plusieurs
    lignes — pas sur les GET par ID (utiliser `get_or_404_scoped` à la place).
    """
    return query.filter(model_class.entreprise_id == user.entreprise_id)


def get_or_404_scoped(
    db: Session, model_class: Type[T], item_id: int, user: User
) -> T:
    """GET par ID + vérification scope.

    Retourne l'objet si trouvé ET appartenant à `user.entreprise_id`.
    Lève 404 si :
    - l'ID n'existe pas dans la BDD
    - OU l'ID existe mais appartient à une autre entreprise (anti-enum)

    Le 404 est volontairement indistinguable entre ces deux cas.
    """
    item = (
        db.query(model_class)
        .filter(
            model_class.id == item_id,
            model_class.entreprise_id == user.entreprise_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model_class.__name__} not found",
        )
    return item


def validate_id_belongs_to_user(
    db: Session, model_class: Type[T], item_id: int, user: User
) -> None:
    """Vérifie qu'un ID externe (passé dans un payload, ex. machine_id sur
    POST /api/cost/calculer) appartient bien à l'entreprise du user.

    Lève 404 si l'ID n'existe pas OU n'appartient pas à `user.entreprise_id`.
    """
    exists = (
        db.query(model_class.id)
        .filter(
            model_class.id == item_id,
            model_class.entreprise_id == user.entreprise_id,
        )
        .first()
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model_class.__name__} {item_id} not found",
        )
