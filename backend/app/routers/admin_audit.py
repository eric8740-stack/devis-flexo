"""Endpoint d'audit temporaire pour diagnostic seeds prod.

Contexte : la prod Railway (plan trial) n'expose pas de shell. Eric ne peut donc
pas faire `python -c "..."` pour inspecter les valeurs réelles de
`developpe_mm` sur `cylindre_magnetique` (suspectées en dents au lieu de mm, ce
qui expliquerait pourquoi le moteur d'optimisation propose 1 pose au lieu de 4
sur le cas test 100×80 mm).

L'endpoint ci-dessous est un contournement explicitement temporaire :
- Réservé `is_admin=True` (Eric uniquement).
- Lit toutes les entreprises (pas de scope tenant) — l'admin a vocation à voir
  les données globales pour faire du support / audit.

**À SUPPRIMER** dès que le diagnostic est terminé et la branche de fix mergée.
Date de création : 2026-05-16.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_admin
from app.models import CylindreMagnetique, Matiere, OptionFabrication, User


router = APIRouter(prefix="/api/admin/audit", tags=["admin-audit-temporaire"])


@router.get("/db-seeds")
def audit_db_seeds(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> dict:
    """État des catalogues seedés en BDD (toutes entreprises confondues).

    Sert UNIQUEMENT au diagnostic ponctuel des seeds prod. Ne pas appeler
    depuis le frontend, ne pas étendre cet endpoint — il sera retiré.
    """
    cylindres = (
        db.query(CylindreMagnetique)
        .order_by(
            CylindreMagnetique.entreprise_id,
            CylindreMagnetique.developpe_mm,
        )
        .all()
    )
    options = (
        db.query(OptionFabrication)
        .order_by(
            OptionFabrication.entreprise_id,
            OptionFabrication.code,
        )
        .all()
    )
    nb_matieres = db.query(Matiere).count()

    return {
        "cylindres": [
            {
                "id": c.id,
                "entreprise_id": c.entreprise_id,
                "developpe_mm": float(c.developpe_mm)
                if c.developpe_mm is not None
                else None,
                "machine_repere": c.machine_repere,
                "actif": c.actif,
            }
            for c in cylindres
        ],
        "options": [
            {
                "id": o.id,
                "entreprise_id": o.entreprise_id,
                "code": o.code,
                "libelle": o.libelle,
                "actif": o.actif,
            }
            for o in options
        ],
        "matieres_count": nb_matieres,
        "counts": {
            "cylindres_total": len(cylindres),
            "options_total": len(options),
        },
    }
