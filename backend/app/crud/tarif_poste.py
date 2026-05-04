"""CRUD tarif_poste — Sprint 12-C scoped par entreprise.

Toutes les fonctions de lecture/modification acceptent `entreprise_id`
pour respecter le scope multi-tenant. Le moteur cost_engine reçoit
`entreprise_id` via `MoteurDevis(db, entreprise_id)` et le passe à
`get_by_cle`.
"""
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


def list_tarifs_poste(
    db: Session, entreprise_id: int, skip: int = 0, limit: int = 50
) -> list[TarifPoste]:
    """Sprint 12-C : filtré par entreprise_id."""
    return (
        db.query(TarifPoste)
        .filter(TarifPoste.entreprise_id == entreprise_id)
        .order_by(TarifPoste.poste_numero, TarifPoste.ordre_affichage, TarifPoste.cle)
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_tarifs_by_poste(
    db: Session, poste_numero: int, entreprise_id: int
) -> list[TarifPoste]:
    """Toutes les clés tarifaires d'un poste donné pour une entreprise."""
    return (
        db.query(TarifPoste)
        .filter(
            TarifPoste.poste_numero == poste_numero,
            TarifPoste.entreprise_id == entreprise_id,
        )
        .order_by(TarifPoste.ordre_affichage, TarifPoste.cle)
        .all()
    )


def get_tarif_poste(db: Session, tarif_id: int) -> TarifPoste | None:
    """Lookup par id (sans scope — usage interne uniquement)."""
    return db.query(TarifPoste).filter(TarifPoste.id == tarif_id).first()


def get_by_cle(
    db: Session, cle: str, entreprise_id: int
) -> TarifPoste | None:
    """Accès par clé symbolique scopé par entreprise.

    Le moteur cost_engine appelle via `MoteurDevis(db, entreprise_id)`.
    Sprint 12-C : `entreprise_id` désormais requis pour le scope.
    """
    return (
        db.query(TarifPoste)
        .filter(
            TarifPoste.cle == cle,
            TarifPoste.entreprise_id == entreprise_id,
        )
        .first()
    )


def create_tarif_poste(
    db: Session, data: TarifPosteCreate, entreprise_id: int
) -> TarifPoste:
    """S12-C : `entreprise_id` injecté par le router via user.entreprise_id."""
    tarif = TarifPoste(entreprise_id=entreprise_id, **data.model_dump())
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
    db: Session, cle: str, valeur_defaut: Decimal, entreprise_id: int
) -> TarifPoste | None:
    """Modifie la valeur courante d'un paramètre pour une entreprise donnée.

    Lève `ValueError` si la valeur sort des bornes valeur_min/valeur_max.
    Le router transforme en 422.
    """
    tarif = get_by_cle(db, cle, entreprise_id)
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
    """Lit seeds/tarif_poste.csv et renvoie {cle: valeur_defaut} pour le poste."""
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


def reset_poste_to_seed_defaults(
    db: Session, poste_numero: int, entreprise_id: int
) -> int:
    """Restaure les valeurs initiales (CSV) du poste pour une entreprise donnée.

    Touche uniquement les lignes appartenant à `entreprise_id`. Si le compte
    n'a pas encore les tarifs (nouveau register), n_reset = 0 (TODO S12-D :
    seed des tarifs par défaut à l'inscription).
    """
    defaults = _load_seed_defaults_for_poste(poste_numero)
    n_reset = 0
    for cle, valeur_seed in defaults.items():
        tarif = get_by_cle(db, cle, entreprise_id)
        if tarif is not None:
            tarif.valeur_defaut = valeur_seed
            n_reset += 1
    db.commit()
    return n_reset
