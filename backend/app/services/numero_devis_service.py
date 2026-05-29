"""Génération automatique du numéro de devis.

Format DEV-YYYY-NNNN, séquence annuelle scopée tenant.

Historique :
  - Sprint 4 Lot 4b : implementation MVP `count(*) + 1`, non scopee tenant,
    non thread-safe. Le commentaire d'epoque annoncait deja le durcissement
    pour le multi-utilisateur.
  - Fix 409 (migration y9n2i3g7d5f0) : passage en `MAX(seq) + 1` scope
    `entreprise_id`. Resout le bug ou un hard-delete entrainait une
    collision UNIQUE (le compteur regenerait le numero du trou bouche).
    La race residuelle est absorbee par le retry loop autour de l'INSERT
    cote `crud.devis.create_devis` / `duplicate_devis`.
"""
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


# Longueur du prefixe `DEV-YYYY-` (9 caracteres). SUBSTR(numero, 10) extrait
# la partie sequentielle a partir du 10e caractere (1-indexe sur SQLite et
# Postgres).
_PREFIX_LEN_PLUS_ONE = 10


def generate_next_numero(db: Session, entreprise_id: int) -> str:
    """Genere DEV-YYYY-NNNN pour le tenant donne (sequence annuelle scopee).

    Strategie : `MAX(CAST(SUBSTR(numero, 10) AS INTEGER)) + 1` parmi les
    devis du tenant pour l'annee courante. Robuste au hard-delete (le trou
    ne sera pas rebouche) et a la coexistence multi-tenant (chaque
    entreprise a son propre compteur).

    Race condition : deux POST simultanes du meme tenant peuvent lire le
    meme MAX et generer le meme numero. C'est le retry loop appelant qui
    absorbe ce cas (cf. `crud.devis.create_devis`).
    """
    annee = datetime.now().year
    prefix = f"DEV-{annee}-"
    max_seq = db.execute(
        text(
            "SELECT COALESCE(MAX(CAST(SUBSTR(numero, "
            f"{_PREFIX_LEN_PLUS_ONE}) AS INTEGER)), 0) "
            "FROM devis "
            "WHERE entreprise_id = :eid AND numero LIKE :pfx"
        ),
        {"eid": entreprise_id, "pfx": f"{prefix}%"},
    ).scalar()
    next_seq = (max_seq or 0) + 1
    return f"{prefix}{next_seq:04d}"
