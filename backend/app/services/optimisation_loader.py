"""Hydrateur Sprint 13 Lot S13.D.7b.

Adapte les modèles SQLAlchemy (Bareme, CylindreMagnetique, MachineImprimerie,
OptionFabrication) en dataclasses du moteur (Cylindre, Machine,
OptionFabrication, barèmes JSON). Scopé par entreprise_id (multi-tenant).

Cette couche fait le pont domaine ↔ persistence et garde le moteur
totalement indépendant de SQLAlchemy.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Bareme,
    CylindreMagnetique,
    MachineImprimerie,
    OptionFabrication,
)
from app.services.optimisation.types import (
    Cylindre,
    Machine,
    OptionFabrication as OptionDC,
)


class OptimisationLoaderError(Exception):
    """Erreur de chargement (ex: option absente du tenant)."""


def charger_cylindres_actifs(
    db: Session, entreprise_id: int
) -> list[Cylindre]:
    rows = (
        db.query(CylindreMagnetique)
        .filter_by(entreprise_id=entreprise_id, actif=True)
        .all()
    )
    return [
        Cylindre(id=r.id, developpe_mm=float(r.developpe_mm))
        for r in rows
    ]


def charger_machines_actives(
    db: Session, entreprise_id: int
) -> list[Machine]:
    rows = (
        db.query(MachineImprimerie)
        .filter_by(entreprise_id=entreprise_id, actif=True)
        .all()
    )
    return [
        Machine(
            id=r.id,
            nom=r.nom,
            laize_utile_mm=float(r.laize_utile_mm),
            nb_groupes_couleurs=r.nb_groupes_couleurs or 0,
            nb_postes_decoupe=r.nb_postes_decoupe or 1,
            vitesse_pratique_m_min=r.vitesse_pratique_m_min,
            cout_horaire_eur=(
                float(r.cout_horaire_eur)
                if r.cout_horaire_eur is not None
                else 0.0
            ),
            options=list(r.options or []),
        )
        for r in rows
    ]


def charger_options_par_codes(
    db: Session, entreprise_id: int, codes: list[str]
) -> list[OptionDC]:
    """Hydrate les options à partir des codes envoyés. Les options peuvent
    être scopées tenant (entreprise_id=user.entreprise_id) OU dans le
    catalogue global (entreprise_id=NULL). Si un code n'existe ni en
    tenant ni en global → OptimisationLoaderError.
    """
    if not codes:
        return []
    rows = (
        db.query(OptionFabrication)
        .filter(OptionFabrication.code.in_(codes))
        .filter(
            (OptionFabrication.entreprise_id == entreprise_id)
            | (OptionFabrication.entreprise_id.is_(None))
        )
        .all()
    )
    # Préfère la row tenant si elle existe pour ce code (override). Sinon
    # on prend la globale.
    by_code: dict[str, OptionFabrication] = {}
    for r in rows:
        if r.code in by_code:
            # On garde la version avec entreprise_id NON-NULL (override tenant)
            if r.entreprise_id is not None:
                by_code[r.code] = r
        else:
            by_code[r.code] = r

    manquants = [c for c in codes if c not in by_code]
    if manquants:
        raise OptimisationLoaderError(
            f"Option(s) non disponible(s) pour votre entreprise : {manquants}. "
            "Vérifiez votre catalogue dans Paramètres > Onboarding express."
        )

    return [
        OptionDC(
            code=r.code,
            libelle=r.libelle,
            groupes_couleurs_requis=r.groupes_couleurs_requis or 0,
            modules_speciaux_requis=list(r.modules_speciaux_requis or []),
            coef_vitesse_impact=float(r.coef_vitesse_impact),
            coef_gache_impact=float(r.coef_gache_impact),
            ajoute_temps_calage_min=r.ajoute_temps_calage_min or 0,
        )
        for r in (by_code[c] for c in codes)
    ]


def charger_baremes(db: Session, entreprise_id: int) -> dict:
    """Renvoie un dict avec les 4 barèmes ICE du tenant (par type).

    Manquant → liste vide (ou dict vide pour confort_roulage). Le moteur
    sait gérer le degraded mode mais c'est anormal en pratique
    (l'onboarding S13.C les crée systématiquement).
    """
    rows = db.query(Bareme).filter_by(entreprise_id=entreprise_id, actif=True).all()
    by_type: dict[str, list | dict] = {}
    for r in rows:
        by_type[r.type] = r.bareme_data
    return {
        "echenillage": by_type.get("echenillage", []),
        "effet_banane": by_type.get("effet_banane", []),
        "compensation_laize_dev": by_type.get("compensation_laize_dev", []),
        "confort_roulage": by_type.get("confort_roulage", {}),
    }
