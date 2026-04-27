"""Peuple la base depuis les CSV de backend/seeds/.

Stratégie : DELETE puis INSERT (idempotent — relançable à l'infini).
Robuste à l'encodage (UTF-8 ou UTF-8-BOM) et au séparateur (, ou ;).
Cellules vides → None en base.

Usage (depuis backend/, venv activé) :

    python -m scripts.seed
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Catalogue,
    ChargeMensuelle,
    Client,
    Complexe,
    Entreprise,
    Fournisseur,
    Machine,
    OperationFinition,
    PartenaireST,
)

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"


def read_csv_rows(filepath: Path) -> list[dict[str, str | None]]:
    """Lit un CSV et renvoie la liste des lignes en dict.

    - utf-8-sig gère UTF-8 avec ou sans BOM.
    - csv.Sniffer détecte le séparateur (, ou ;) à partir d'un échantillon.
    - Les cellules vides sont converties en None (pas en chaîne vide).
    """
    with filepath.open(encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        return [
            {k: (v.strip() if v and v.strip() else None) for k, v in row.items()}
            for row in reader
        ]


def parse_date(value: str | None) -> date | None:
    """Parse une date au format ISO (YYYY-MM-DD) ou français (DD/MM/YYYY)."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Format de date non reconnu : {value!r}")


def _to_int(value: str | None) -> int | None:
    return int(value) if value else None


def _to_float(value: str | None) -> float | None:
    return float(value) if value else None


def seed_entreprise(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "entreprise.csv")
    session.query(Entreprise).delete()
    for row in rows:
        session.add(
            Entreprise(
                id=_to_int(row["id"]),
                raison_sociale=row["raison_sociale"],
                siret=row["siret"],
                adresse=row.get("adresse"),
                cp=row.get("cp"),
                ville=row.get("ville"),
                tel=row.get("tel"),
                email=row.get("email"),
                pct_fg=_to_float(row.get("pct_fg")),
                pct_marge_defaut=_to_float(row.get("pct_marge_defaut")),
                heures_prod_presse_mois=_to_int(row.get("heures_prod_presse_mois")),
                heures_prod_finition_mois=_to_int(row.get("heures_prod_finition_mois")),
            )
        )
    return len(rows)


def seed_client(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "client.csv")
    session.query(Client).delete()
    for row in rows:
        session.add(
            Client(
                id=_to_int(row["id"]),
                raison_sociale=row["raison_sociale"],
                siret=row.get("siret"),
                adresse_fact=row.get("adresse_fact"),
                cp_fact=row.get("cp_fact"),
                ville_fact=row.get("ville_fact"),
                contact=row.get("contact"),
                email=row.get("email"),
                tel=row.get("tel"),
                segment=row.get("segment"),
                date_creation=parse_date(row.get("date_creation")),
            )
        )
    return len(rows)


def seed_fournisseur(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "fournisseur.csv")
    session.query(Fournisseur).delete()
    for row in rows:
        session.add(
            Fournisseur(
                id=_to_int(row["id"]),
                raison_sociale=row["raison_sociale"],
                categorie=row.get("categorie"),
                contact=row.get("contact"),
                email=row.get("email"),
                tel=row.get("tel"),
                conditions_paiement=row.get("conditions_paiement"),
                delai_livraison_j=_to_int(row.get("delai_livraison_j")),
            )
        )
    return len(rows)


def run_seed() -> dict[str, int]:
    """Exécute tous les seeders dans une seule transaction.

    Returns: dict {"entreprise": N, "client": N, "fournisseur": N}
    """
    counts: dict[str, int] = {}
    with SessionLocal() as session:
        # Vider d'abord les tables S2 qui ont des FK vers client/fournisseur
        # (catalogue.client_id RESTRICT, complexe.fournisseur_id SET NULL)
        # sinon `DELETE FROM client` plante avec FOREIGN KEY constraint failed.
        # Les autres tables S2 sont vidées par symétrie (tests reproductibles).
        # Les INSERT pour ces tables viendront au Lot 4 (seed S2).
        session.query(Catalogue).delete()
        session.query(Complexe).delete()
        session.query(Machine).delete()
        session.query(OperationFinition).delete()
        session.query(PartenaireST).delete()
        session.query(ChargeMensuelle).delete()

        counts["entreprise"] = seed_entreprise(session)
        counts["client"] = seed_client(session)
        counts["fournisseur"] = seed_fournisseur(session)
        session.commit()
    return counts


def main() -> None:
    counts = run_seed()
    print(f"Entreprise  : {counts['entreprise']} ligne insérée.")
    print(f"Client      : {counts['client']} lignes insérées.")
    print(f"Fournisseur : {counts['fournisseur']} lignes insérées.")


if __name__ == "__main__":
    main()
