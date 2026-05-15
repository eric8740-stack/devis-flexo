"""Service d'onboarding express Sprint 13 Lot S13.C.

Logique métier pure (pas de FastAPI ici) : à partir d'une sélection
d'éléments du catalogue par défaut, instancie les rows en base pour
le tenant. Utilisé par le router `onboarding_router.py`.

Décisions :
  - Idempotence stricte : si le tenant a DÉJÀ des rows dans l'une des
    5 tables S13.B (cylindre_magnetique, machine_imprimerie, matiere,
    option_fabrication scoped, bareme), on REFUSE (409). L'utilisateur
    doit explicitement passer `force=True` pour vider+recharger.
  - Barèmes : TOUJOURS chargés (les 4 sont fondamentaux pour le moteur),
    le user ne les décoche pas — c'est juste un check_box "j'accepte
    les barèmes ICE par défaut" côté UI.
  - Options de fabrication : on les copie dans le tenant (entreprise_id
    set sur le user) pour que l'imprimerie puisse les surcharger
    (prix, coefs). Pas de partage du catalogue global pour l'instant.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.data.catalogue_defaults import (
    BAREMES_DEFAULT,
    CYLINDRES_STANDARD_MM,
    MACHINES_DEFAULT,
    MATIERES_DEFAULT,
    OPTIONS_FABRICATION_DEFAULT,
    get_machine_by_code,
    get_matiere_by_code,
    get_option_by_code,
)
from app.models import (
    Bareme,
    CylindreMagnetique,
    MachineImprimerie,
    Matiere,
    OptionFabrication,
)


class OnboardingError(Exception):
    """Erreur fonctionnelle remontée au router pour HTTP 409/422."""


def has_existing_catalogue(db: Session, entreprise_id: int) -> bool:
    """Vrai si le tenant a déjà au moins une row dans l'une des 5 tables
    S13.B (autres que option_fabrication globale qui ne nous concerne pas).
    """
    if db.query(CylindreMagnetique).filter_by(entreprise_id=entreprise_id).first():
        return True
    if db.query(MachineImprimerie).filter_by(entreprise_id=entreprise_id).first():
        return True
    if db.query(Matiere).filter_by(entreprise_id=entreprise_id).first():
        return True
    if db.query(OptionFabrication).filter_by(entreprise_id=entreprise_id).first():
        return True
    if db.query(Bareme).filter_by(entreprise_id=entreprise_id).first():
        return True
    return False


def _validate_codes(
    field: str, requested: list[Any], allowed: set[Any]
) -> None:
    invalid = [r for r in requested if r not in allowed]
    if invalid:
        raise OnboardingError(
            f"{field} : codes inconnus dans le catalogue défaut : {invalid}"
        )


def initialiser_catalogues(
    db: Session,
    entreprise_id: int,
    cylindres_developpes_mm: list[float],
    machines_codes: list[str],
    matieres_codes: list[str],
    options_codes: list[str],
) -> dict[str, int]:
    """Initialise les catalogues pour un tenant à partir d'une sélection.

    Retourne les compteurs créés. Lève OnboardingError si déjà initialisé
    ou si un code envoyé n'existe pas dans le catalogue défaut.
    """
    if has_existing_catalogue(db, entreprise_id):
        raise OnboardingError(
            "Catalogue déjà initialisé pour cette entreprise. "
            "Refuse pour éviter doublons. "
            "Supprimez les rows existantes avant de relancer l'onboarding."
        )

    # Validation des codes envoyés (fail fast avant tout INSERT)
    _validate_codes(
        "cylindres_developpes_mm",
        cylindres_developpes_mm,
        set(CYLINDRES_STANDARD_MM),
    )
    _validate_codes(
        "machines_codes",
        machines_codes,
        {m["code"] for m in MACHINES_DEFAULT},
    )
    _validate_codes(
        "matieres_codes",
        matieres_codes,
        {m["code"] for m in MATIERES_DEFAULT},
    )
    _validate_codes(
        "options_codes",
        options_codes,
        {o["code"] for o in OPTIONS_FABRICATION_DEFAULT},
    )

    counts = {
        "cylindres": 0,
        "machines": 0,
        "matieres": 0,
        "options": 0,
        "baremes": 0,
    }

    # --- Cylindres : developpe_mm seul, inventaire à 0 ---------------------
    for dev_mm in cylindres_developpes_mm:
        db.add(
            CylindreMagnetique(
                entreprise_id=entreprise_id,
                developpe_mm=Decimal(str(dev_mm)),
            )
        )
        counts["cylindres"] += 1

    # --- Machines ---------------------------------------------------------
    for code in machines_codes:
        spec = get_machine_by_code(code)
        if spec is None:  # déjà validé mais ceinture+bretelles
            continue
        db.add(
            MachineImprimerie(
                entreprise_id=entreprise_id,
                nom=spec["nom"],
                marque=spec.get("marque"),
                modele=spec.get("modele"),
                repere_court=spec.get("repere_court"),
                laize_totale_mm=Decimal(str(spec["laize_totale_mm"])),
                laize_utile_mm=Decimal(str(spec["laize_utile_mm"])),
                nb_groupes_couleurs=spec.get("nb_groupes_couleurs"),
                nb_postes_decoupe=spec.get("nb_postes_decoupe", 1),
                vitesse_nominale_constructeur_m_min=spec.get(
                    "vitesse_nominale_constructeur_m_min"
                ),
                vitesse_pratique_m_min=spec["vitesse_pratique_m_min"],
                cout_horaire_eur=(
                    Decimal(str(spec["cout_horaire_eur"]))
                    if spec.get("cout_horaire_eur") is not None
                    else None
                ),
                options=spec.get("options"),
                type_encre_supportee=spec.get("type_encre_supportee"),
                notes=spec.get("notes"),
            )
        )
        counts["machines"] += 1

    # --- Matières ---------------------------------------------------------
    for code in matieres_codes:
        spec = get_matiere_by_code(code)
        if spec is None:
            continue
        db.add(
            Matiere(
                entreprise_id=entreprise_id,
                code=spec["code"],
                libelle=spec["libelle"],
                categorie=spec.get("categorie"),
                sous_type=spec.get("sous_type"),
                grammage_gm2=spec.get("grammage_gm2"),
                epaisseur_microns=spec.get("epaisseur_microns"),
                adhesifs_compatibles=spec.get("adhesifs_compatibles"),
                est_transparent=spec.get("est_transparent", False),
                opacite_pct=(
                    Decimal(str(spec["opacite_pct"]))
                    if spec.get("opacite_pct") is not None
                    else None
                ),
                certifications_sanitaires=spec.get("certifications_sanitaires"),
                certifications_env=spec.get("certifications_env"),
                notes_techniques=spec.get("notes_techniques"),
            )
        )
        counts["matieres"] += 1

    # --- Options fabrication ----------------------------------------------
    for code in options_codes:
        spec = get_option_by_code(code)
        if spec is None:
            continue
        db.add(
            OptionFabrication(
                entreprise_id=entreprise_id,
                code=spec["code"],
                libelle=spec["libelle"],
                categorie=spec.get("categorie"),
                description=spec.get("description"),
                ajoute_cliches=spec.get("ajoute_cliches", 0),
                ajoute_couleurs=spec.get("ajoute_couleurs", 0),
                ajoute_outils_decoupe=spec.get("ajoute_outils_decoupe", 0),
                groupes_couleurs_requis=spec.get("groupes_couleurs_requis", 0),
                modules_speciaux_requis=spec.get("modules_speciaux_requis"),
                est_silhouette_auto=spec.get("est_silhouette_auto", False),
                ajoute_temps_calage_min=spec.get("ajoute_temps_calage_min", 0),
                coef_vitesse_impact=Decimal(
                    str(spec.get("coef_vitesse_impact", "1.00"))
                ),
                coef_gache_impact=Decimal(
                    str(spec.get("coef_gache_impact", "1.00"))
                ),
            )
        )
        counts["options"] += 1

    # --- Barèmes : TOUS chargés systématiquement --------------------------
    for spec in BAREMES_DEFAULT:
        db.add(
            Bareme(
                entreprise_id=entreprise_id,
                type=spec["type"],
                nom=spec["nom"],
                bareme_data=spec["bareme_data"],
                notes=spec.get("notes"),
            )
        )
        counts["baremes"] += 1

    db.commit()
    return counts
