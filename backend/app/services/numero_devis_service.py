"""Génération automatique du numéro de devis (Sprint 4 Lot 4b).

Format DEV-YYYY-NNNN avec séquence annuelle (compteur des devis créés
sur l'année en cours, +1, padded 4 digits).

⚠️ MVP : approche `count + 1` non thread-safe. Pour multi-utilisateurs
prod, prévoir séquence Postgres dédiée (à durcir Sprint 6+ avec auth).
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Devis


def generate_next_numero(db: Session) -> str:
    """Génère DEV-YYYY-NNNN (séquence annuelle, padded 4 digits)."""
    annee = datetime.now().year
    count = (
        db.query(Devis)
        .filter(Devis.numero.like(f"DEV-{annee}-%"))
        .count()
    )
    next_seq = count + 1
    return f"DEV-{annee}-{next_seq:04d}"
