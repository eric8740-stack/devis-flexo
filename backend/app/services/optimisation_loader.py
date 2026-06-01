"""Hydrateur Sprint 13 Lot S13.D.7b.

Adapte les modèles SQLAlchemy (Bareme, CylindreMagnetique, Machine,
OptionFabrication) en dataclasses du moteur (Cylindre, Machine,
OptionFabrication, barèmes JSON). Scopé par entreprise_id (multi-tenant).

B3a (convergence option B, 2026-06-01) : `charger_machines_actives` lit
désormais `Machine` (parc réel utilisateur) au lieu de `MachineImprimerie`
(legacy catalogue). La `vitesse_pratique_m_min` du dataclass moteur est
dérivée à la volée : `round(vitesse_moyenne_m_h / 60)` -- une seule vitesse
réelle, alignée avec /machines + Stratégique > Machines (B2).

Cette couche fait le pont domaine ↔ persistence et garde le moteur
totalement indépendant de SQLAlchemy.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Bareme,
    CylindreMagnetique,
    Machine as MachineORM,
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
    """Hydrate les machines actives du parc utilisateur en dataclasses moteur.

    B3a : lit le modele `Machine` (CRUD /machines, edite par l'imprimeur)
    au lieu de `MachineImprimerie` (legacy catalogue, deprecie). Garantit
    que l'etape 2 « Candidats viables » affiche le parc reel (P5/Daco/
    Atelier 2 pour le tenant demo) et non plus les references catalogue
    (Mark Andy 2200 / OMET XFlex 330 / Nilpeter FA-22).

    Derivations / fallbacks :
      - `vitesse_pratique_m_min` (dataclass moteur) <-
        `round(vitesse_moyenne_m_h / 60)` (m/h -> m/min). Une seule vitesse
        reelle, partagee avec le cost_engine (SACRED V1a 1 449,09 EUR).
      - `laize_utile_mm` -> fallback sur `laize_max_mm` si NULL (cas
        nouveaux tenants pas encore configures via UI B2). Cohérent avec
        la data migration tenant demo (laize_utile := laize_max).
      - `nb_groupes_couleurs` -> 0 si NULL (machine sans impression, ex.
        Daco D250 ligne finition -> exclue automatiquement par le filtre
        dur capacite couleurs des qu'une couleur est demandee).
      - `nb_postes_decoupe` -> 1 si NULL (server_default migration B1
        z0p4n6r8s1t3).
      - `cout_horaire_eur` -> 0.0 si NULL.
      - `options` -> [] si NULL.

    Une machine sans `vitesse_moyenne_m_h` est SILENCIEUSEMENT ECARTEE
    (vitesse_pratique = 0 casserait le scoring). En pratique, l'UI rend
    le champ « Vitesse réelle de production » obligatoire (B2), donc le
    cas reste theorique pour les machines saisies via l'interface.
    """
    rows = (
        db.query(MachineORM)
        .filter_by(entreprise_id=entreprise_id, actif=True)
        .all()
    )
    machines: list[Machine] = []
    for r in rows:
        if r.vitesse_moyenne_m_h is None or r.vitesse_moyenne_m_h <= 0:
            # Pas de vitesse reelle -> machine non utilisable par le moteur.
            # Aucun crash : l'UI etape 2 affichera juste un parc reduit.
            continue
        vitesse_m_min = int(round(r.vitesse_moyenne_m_h / 60))
        # laize_utile_mm peut etre NULL (nouveau tenant non configure B2).
        # Fallback sur laize_max_mm (NOT NULL en BDD) = comportement
        # raisonnable par defaut.
        laize_utile_val = (
            r.laize_utile_mm if r.laize_utile_mm is not None else r.laize_max_mm
        )
        machines.append(
            Machine(
                id=r.id,
                nom=r.nom,
                laize_utile_mm=float(laize_utile_val),
                nb_groupes_couleurs=r.nb_groupes_couleurs or 0,
                nb_postes_decoupe=r.nb_postes_decoupe or 1,
                vitesse_pratique_m_min=vitesse_m_min,
                cout_horaire_eur=(
                    float(r.cout_horaire_eur)
                    if r.cout_horaire_eur is not None
                    else 0.0
                ),
                options=list(r.options or []),
            )
        )
    return machines


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
