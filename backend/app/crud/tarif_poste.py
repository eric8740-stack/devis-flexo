import csv
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import TarifPoste
from app.schemas.tarif_poste import TarifPosteCreate, TarifPosteUpdate

# Sprint 9 v2 — Path vers seeds/tarif_poste.csv pour le reset par poste
_SEEDS_TARIF_POSTE_CSV = (
    Path(__file__).resolve().parent.parent.parent / "seeds" / "tarif_poste.csv"
)


def list_tarifs_poste(db: Session, skip: int = 0, limit: int = 50) -> list[TarifPoste]:
    return (
        db.query(TarifPoste)
        .order_by(TarifPoste.poste_numero, TarifPoste.ordre_affichage, TarifPoste.cle)
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_tarifs_by_poste(db: Session, poste_numero: int) -> list[TarifPoste]:
    """Toutes les clés tarifaires d'un poste donné, triées par ordre_affichage."""
    return (
        db.query(TarifPoste)
        .filter(TarifPoste.poste_numero == poste_numero)
        .order_by(TarifPoste.ordre_affichage, TarifPoste.cle)
        .all()
    )


def get_tarif_poste(db: Session, tarif_id: int) -> TarifPoste | None:
    return db.query(TarifPoste).filter(TarifPoste.id == tarif_id).first()


def get_by_cle(db: Session, cle: str) -> TarifPoste | None:
    """Accès par clé symbolique (`matiere_prix_kg_defaut`, ...) pour le moteur v2.

    Le moteur de calcul (Lot 3d) appelle uniquement par cle, jamais par id ni
    libellé — un changement de texte ne casse pas la logique.
    """
    return db.query(TarifPoste).filter(TarifPoste.cle == cle).first()


def create_tarif_poste(db: Session, data: TarifPosteCreate) -> TarifPoste:
    # S12-A : entreprise_id=1 (compte demo). S12-C remplacera par user.entreprise_id
    tarif = TarifPoste(entreprise_id=1, **data.model_dump())
    db.add(tarif)
    db.commit()
    db.refresh(tarif)
    return tarif


def update_tarif_poste(
    db: Session, tarif_id: int, data: TarifPosteUpdate
) -> TarifPoste | None:
    tarif = get_tarif_poste(db, tarif_id)
    if tarif is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tarif, field, value)
    db.commit()
    db.refresh(tarif)
    return tarif


def update_valeur_by_cle(
    db: Session, cle: str, valeur_defaut: Decimal
) -> TarifPoste | None:
    """Sprint 9 v2 — modifie uniquement la valeur courante d'un paramètre.

    Si le tarif a `valeur_min`/`valeur_max` définis, la nouvelle valeur doit
    être dans la plage — sinon `ValueError` (le router transforme en 422).
    """
    tarif = get_by_cle(db, cle)
    if tarif is None:
        return None
    if tarif.valeur_min is not None and valeur_defaut < tarif.valeur_min:
        raise ValueError(
            f"valeur_defaut={valeur_defaut} < valeur_min={tarif.valeur_min} "
            f"pour la clé {cle!r}"
        )
    if tarif.valeur_max is not None and valeur_defaut > tarif.valeur_max:
        raise ValueError(
            f"valeur_defaut={valeur_defaut} > valeur_max={tarif.valeur_max} "
            f"pour la clé {cle!r}"
        )
    tarif.valeur_defaut = valeur_defaut
    db.commit()
    db.refresh(tarif)
    return tarif


def _load_seed_defaults_for_poste(poste_numero: int) -> dict[str, Decimal]:
    """Lit seeds/tarif_poste.csv et renvoie {cle: valeur_defaut} pour le poste.

    Source unique des valeurs initiales (cohérent avec scripts/seed.py).
    """
    defaults: dict[str, Decimal] = {}
    with _SEEDS_TARIF_POSTE_CSV.open(encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            if int(row["poste_numero"]) == poste_numero:
                defaults[row["cle"]] = Decimal(row["valeur_defaut"])
    return defaults


def reset_poste_to_seed_defaults(db: Session, poste_numero: int) -> int:
    """Sprint 9 v2 — restaure les valeurs initiales (CSV) du poste.

    Renvoie le nombre de lignes effectivement remises à leur valeur seed.
    Lignes en BDD non présentes dans le CSV (créées dynamiquement) ne sont
    pas touchées.
    """
    defaults = _load_seed_defaults_for_poste(poste_numero)
    n_reset = 0
    for cle, valeur_seed in defaults.items():
        tarif = get_by_cle(db, cle)
        if tarif is not None:
            tarif.valeur_defaut = valeur_seed
            n_reset += 1
    db.commit()
    return n_reset
