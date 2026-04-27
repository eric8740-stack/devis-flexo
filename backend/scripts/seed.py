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


# ---------------------------------------------------------------------------
# Sprint 0-1 : entreprise / client / fournisseur
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Sprint 2 : 6 nouvelles tables
# ---------------------------------------------------------------------------


def seed_machine(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "machine.csv")
    for row in rows:
        session.add(
            Machine(
                id=_to_int(row["id"]),
                nom=row["nom"],
                largeur_max_mm=_to_int(row.get("largeur_max_mm")),
                vitesse_max_m_min=_to_int(row.get("vitesse_max_m_min")),
                nb_couleurs=_to_int(row.get("nb_couleurs")),
                cout_horaire_eur=_to_float(row.get("cout_horaire_eur")),
                statut=row.get("statut") or "actif",
                commentaire=row.get("commentaire"),
            )
        )
    return len(rows)


def seed_operation_finition(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "operation_finition.csv")
    for row in rows:
        session.add(
            OperationFinition(
                id=_to_int(row["id"]),
                nom=row["nom"],
                unite_facturation=row["unite_facturation"],
                cout_unitaire_eur=_to_float(row.get("cout_unitaire_eur")),
                temps_minutes_unite=_to_float(row.get("temps_minutes_unite")),
                statut=row.get("statut") or "actif",
                commentaire=row.get("commentaire"),
            )
        )
    return len(rows)


def seed_partenaire_st(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "partenaire_st.csv")
    for row in rows:
        session.add(
            PartenaireST(
                id=_to_int(row["id"]),
                raison_sociale=row["raison_sociale"],
                siret=row.get("siret"),
                contact_nom=row.get("contact_nom"),
                contact_email=row.get("contact_email"),
                contact_tel=row.get("contact_tel"),
                prestation_type=row.get("prestation_type"),
                delai_jours_moyen=_to_int(row.get("delai_jours_moyen")),
                qualite_score=_to_int(row.get("qualite_score")),
                commentaire=row.get("commentaire"),
                statut=row.get("statut") or "actif",
            )
        )
    return len(rows)


def seed_charge_mensuelle(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "charge_mensuelle.csv")
    for row in rows:
        session.add(
            ChargeMensuelle(
                id=_to_int(row["id"]),
                libelle=row["libelle"],
                categorie=row["categorie"],
                montant_eur=_to_float(row["montant_eur"]),
                date_debut=parse_date(row["date_debut"]),
                date_fin=parse_date(row.get("date_fin")),
                commentaire=row.get("commentaire"),
            )
        )
    return len(rows)


def seed_complexe(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "complexe.csv")
    for row in rows:
        session.add(
            Complexe(
                id=_to_int(row["id"]),
                reference=row["reference"],
                famille=row["famille"],
                face_matiere=row.get("face_matiere"),
                grammage_g_m2=_to_int(row.get("grammage_g_m2")),
                adhesif_type=row.get("adhesif_type"),
                prix_m2_eur=_to_float(row["prix_m2_eur"]),
                fournisseur_id=_to_int(row.get("fournisseur_id")),
                statut=row.get("statut") or "actif",
                commentaire=row.get("commentaire"),
            )
        )
    return len(rows)


def seed_catalogue(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "catalogue.csv")
    for row in rows:
        session.add(
            Catalogue(
                id=_to_int(row["id"]),
                code_produit=row["code_produit"],
                designation=row["designation"],
                client_id=_to_int(row["client_id"]),
                machine_id=_to_int(row.get("machine_id")),
                matiere=row.get("matiere"),
                format_mm=row.get("format_mm"),
                nb_couleurs=_to_int(row.get("nb_couleurs")),
                prix_unitaire_eur=_to_float(row.get("prix_unitaire_eur")),
                frequence_estimee=row.get("frequence_estimee"),
                commentaire=row.get("commentaire"),
                statut=row.get("statut") or "actif",
            )
        )
    return len(rows)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_seed() -> dict[str, int]:
    """Exécute tous les seeders dans une seule transaction.

    Ordre :
    1. DELETE descendant : enfants (catalogue, complexe) AVANT parents
       (client, fournisseur, machine) pour éviter les violations FK
       (catalogue.client_id RESTRICT, complexe.fournisseur_id SET NULL,
       catalogue.machine_id SET NULL).
    2. INSERT ascendant via les fonctions seed_xxx + `session.flush()`
       après chaque table pour rendre les parents visibles aux enfants.
       Sans flush, SQLAlchemy n'ordonne pas correctement les INSERTs
       quand les FK sont déclarées sans `relationship()` → PostgreSQL
       refuse l'INSERT enfant car le parent n'est pas encore en base
       (ForeignKeyViolation). SQLite est plus laxiste et accepte.
    """
    counts: dict[str, int] = {}
    with SessionLocal() as session:
        # Phase 1 — DELETE descendant des tables enfants (S2)
        session.query(Catalogue).delete()
        session.query(Complexe).delete()
        session.query(Machine).delete()
        session.query(OperationFinition).delete()
        session.query(PartenaireST).delete()
        session.query(ChargeMensuelle).delete()
        session.flush()  # commit logique des DELETE en transaction

        # Phase 2 — INSERT ascendant + flush entre chaque pour respecter FK
        for name, fn in (
            ("entreprise", seed_entreprise),
            ("client", seed_client),
            ("fournisseur", seed_fournisseur),
            ("machine", seed_machine),
            ("operation_finition", seed_operation_finition),
            ("partenaire_st", seed_partenaire_st),
            ("charge_mensuelle", seed_charge_mensuelle),
            ("complexe", seed_complexe),  # FK fournisseur
            ("catalogue", seed_catalogue),  # FK client + machine
        ):
            counts[name] = fn(session)
            session.flush()

        session.commit()
    return counts


def main() -> None:
    counts = run_seed()
    print("=== Sprint 0-1 ===")
    print(f"Entreprise          : {counts['entreprise']}")
    print(f"Client              : {counts['client']}")
    print(f"Fournisseur         : {counts['fournisseur']}")
    print("=== Sprint 2 ===")
    print(f"Machine             : {counts['machine']}")
    print(f"OperationFinition   : {counts['operation_finition']}")
    print(f"PartenaireST        : {counts['partenaire_st']}")
    print(f"ChargeMensuelle     : {counts['charge_mensuelle']}")
    print(f"Complexe            : {counts['complexe']}")
    print(f"Catalogue           : {counts['catalogue']}")
    print(f"\nTotal : {sum(counts.values())} lignes insérées.")


if __name__ == "__main__":
    main()
