from sqlalchemy.orm import Session

from app.models import OutilDecoupe
from app.schemas.outil_decoupe import OutilDecoupeCreate, OutilDecoupeUpdate


def get_outil_decoupe(db: Session, outil_id: int) -> OutilDecoupe | None:
    return db.query(OutilDecoupe).filter(OutilDecoupe.id == outil_id).first()


def list_outils_decoupe_actifs(db: Session) -> list[OutilDecoupe]:
    """Pour le select catalogue côté frontend (Lot 5d).

    Filtre `actif = True` (soft delete). Pas de pagination : on attend
    moins de 100 outils en pratique.
    """
    return (
        db.query(OutilDecoupe)
        .filter(OutilDecoupe.actif.is_(True))
        .order_by(OutilDecoupe.libelle)
        .all()
    )


def list_outils_decoupe(
    db: Session, include_inactives: bool = False
) -> list[OutilDecoupe]:
    """Sprint 9 v2 — liste pour l'UI /parametres/outils.

    `include_inactives=False` (default) → seulement actifs (compat select Lot 5d).
    `include_inactives=True` → tous (UI paramètres avec toggle "Afficher inactifs").
    """
    query = db.query(OutilDecoupe)
    if not include_inactives:
        query = query.filter(OutilDecoupe.actif.is_(True))
    return query.order_by(OutilDecoupe.libelle).all()


def create_outil_decoupe(
    db: Session, data: OutilDecoupeCreate
) -> OutilDecoupe:
    outil = OutilDecoupe(**data.model_dump())
    db.add(outil)
    db.commit()
    db.refresh(outil)
    return outil


def update_outil_decoupe(
    db: Session, outil_id: int, data: OutilDecoupeUpdate
) -> OutilDecoupe | None:
    outil = get_outil_decoupe(db, outil_id)
    if outil is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(outil, field, value)
    db.commit()
    db.refresh(outil)
    return outil


def soft_delete_outil_decoupe(db: Session, outil_id: int) -> bool:
    """Sprint 9 v2 — passe `actif=False` (cohérent pattern catalogues)."""
    outil = get_outil_decoupe(db, outil_id)
    if outil is None:
        return False
    outil.actif = False
    db.commit()
    return True


def reactiver_outil_decoupe(db: Session, outil_id: int) -> bool:
    """Sprint 9 v2 — passe `actif=True` pour réintroduire un outil archivé."""
    outil = get_outil_decoupe(db, outil_id)
    if outil is None:
        return False
    outil.actif = True
    db.commit()
    return True
