from sqlalchemy.orm import Session

from app.models import OutilDecoupe


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
