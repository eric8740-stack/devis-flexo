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
    ChargeMachineMensuelle,
    ChargeMensuelle,
    Client,
    Complexe,
    CorrespondanceLaizeMetrage,
    Entreprise,
    Fournisseur,
    Machine,
    OperationFinition,
    OutilDecoupe,
    PartenaireST,
    TarifEncre,
    TarifPoste,
    TempsOperationStandard,
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


def _to_bool(value: str | None) -> bool:
    # CSV n'a pas de type natif boolean — on accepte true/1/yes (insensible casse).
    if value is None:
        return False
    return value.strip().lower() in ("true", "1", "yes")


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
        # Sprint 9 v2 — `actif` Boolean (refactor depuis statut String)
        actif_val = row.get("actif")
        actif = _to_bool(actif_val) if actif_val is not None else True
        session.add(
            Machine(
                id=_to_int(row["id"]),
                nom=row["nom"],
                largeur_max_mm=_to_int(row.get("largeur_max_mm")),
                laize_max_mm=_to_float(row.get("laize_max_mm")),
                vitesse_max_m_min=_to_int(row.get("vitesse_max_m_min")),
                nb_couleurs=_to_int(row.get("nb_couleurs")),
                cout_horaire_eur=_to_float(row.get("cout_horaire_eur")),
                vitesse_moyenne_m_h=_to_int(row.get("vitesse_moyenne_m_h")),
                duree_calage_h=_to_float(row.get("duree_calage_h")),
                actif=actif,
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
        # Sprint 9 v2 — `actif` Boolean (refactor depuis statut String)
        actif_val = row.get("actif")
        actif = _to_bool(actif_val) if actif_val is not None else True
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
                actif=actif,
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
        # Sprint 9 v2 — `actif` Boolean (refactor depuis statut String)
        actif_val = row.get("actif")
        actif = _to_bool(actif_val) if actif_val is not None else True
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
                actif=actif,
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
# Sprint 3 Lot 3b : 5 tables paramétriques du moteur de coût v2
# ---------------------------------------------------------------------------


def seed_tarif_poste(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "tarif_poste.csv")
    for row in rows:
        # Sprint 9 v2 — colonnes description (Text NULL) + ordre_affichage (Integer)
        ordre_val = row.get("ordre_affichage")
        ordre = _to_int(ordre_val) if ordre_val is not None else 0
        session.add(
            TarifPoste(
                id=_to_int(row["id"]),
                cle=row["cle"],
                poste_numero=_to_int(row["poste_numero"]),
                libelle=row["libelle"],
                valeur_defaut=_to_float(row["valeur_defaut"]),
                valeur_min=_to_float(row.get("valeur_min")),
                valeur_max=_to_float(row.get("valeur_max")),
                unite=row["unite"],
                actif=_to_bool(row.get("actif")),
                description=row.get("description"),
                ordre_affichage=ordre or 0,
            )
        )
    return len(rows)


def seed_tarif_encre(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "tarif_encre.csv")
    for row in rows:
        session.add(
            TarifEncre(
                id=_to_int(row["id"]),
                type_encre=row["type_encre"],
                libelle=row["libelle"],
                prix_kg_defaut=_to_float(row["prix_kg_defaut"]),
                prix_kg_min=_to_float(row.get("prix_kg_min")),
                prix_kg_max=_to_float(row.get("prix_kg_max")),
                ratio_g_m2_couleur=_to_float(row["ratio_g_m2_couleur"]),
                actif=_to_bool(row.get("actif")),
            )
        )
    return len(rows)


def seed_temps_operation_standard(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "temps_operation_standard.csv")
    for row in rows:
        session.add(
            TempsOperationStandard(
                id=_to_int(row["id"]),
                libelle_operation=row["libelle_operation"],
                minutes_standard=_to_float(row["minutes_standard"]),
                categorie=row.get("categorie"),
                ordre_affichage=_to_int(row["ordre_affichage"]),
                actif=_to_bool(row.get("actif")),
            )
        )
    return len(rows)


def seed_correspondance_laize_metrage(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "correspondance_laize_metrage.csv")
    for row in rows:
        session.add(
            CorrespondanceLaizeMetrage(
                id=_to_int(row["id"]),
                laize_mm=_to_int(row["laize_mm"]),
                metrage_metres=_to_int(row["metrage_metres"]),
            )
        )
    return len(rows)


def seed_outil_decoupe(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "outil_decoupe.csv")
    for row in rows:
        session.add(
            OutilDecoupe(
                id=_to_int(row["id"]),
                libelle=row["libelle"],
                format_l_mm=_to_int(row["format_l_mm"]),
                format_h_mm=_to_int(row["format_h_mm"]),
                nb_poses_l=_to_int(row["nb_poses_l"]),
                nb_poses_h=_to_int(row["nb_poses_h"]),
                forme_speciale=_to_bool(row.get("forme_speciale")),
                actif=_to_bool(row.get("actif")),
            )
        )
    return len(rows)


def seed_charge_machine_mensuelle(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "charge_machine_mensuelle.csv")
    for row in rows:
        # cout_horaire_calcule absent volontairement : le hook before_insert
        # le calcule à partir de montant_total / heures_disponibles.
        session.add(
            ChargeMachineMensuelle(
                id=_to_int(row["id"]),
                mois=_to_int(row["mois"]),
                annee=_to_int(row["annee"]),
                montant_total=_to_float(row["montant_total"]),
                heures_disponibles=_to_float(row["heures_disponibles"]),
                source=row.get("source"),
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
        # Phase 1 — DELETE descendant des tables enfants (S2 + S3 Lot 3b)
        session.query(Catalogue).delete()
        session.query(Complexe).delete()
        session.query(Machine).delete()
        session.query(OperationFinition).delete()
        session.query(PartenaireST).delete()
        session.query(ChargeMensuelle).delete()
        # Tables S3 Lot 3b — pas de FK entre elles ni vers les autres,
        # ordre libre. Groupées ici pour visibilité.
        session.query(TarifPoste).delete()
        session.query(TarifEncre).delete()
        session.query(TempsOperationStandard).delete()
        session.query(CorrespondanceLaizeMetrage).delete()
        session.query(ChargeMachineMensuelle).delete()
        # S5
        session.query(OutilDecoupe).delete()
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
            # S3 Lot 3b — référentiels paramétriques moteur v2
            ("tarif_poste", seed_tarif_poste),
            ("tarif_encre", seed_tarif_encre),
            ("temps_operation_standard", seed_temps_operation_standard),
            ("correspondance_laize_metrage", seed_correspondance_laize_metrage),
            ("charge_machine_mensuelle", seed_charge_machine_mensuelle),
            # S5 Lot 5a — catalogue outils de découpe
            ("outil_decoupe", seed_outil_decoupe),
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
    print("=== Sprint 3 Lot 3b ===")
    print(f"TarifPoste          : {counts['tarif_poste']}")
    print(f"TarifEncre          : {counts['tarif_encre']}")
    print(f"TempsOpStandard     : {counts['temps_operation_standard']}")
    print(f"LaizeMetrage        : {counts['correspondance_laize_metrage']}")
    print(f"ChargeMachineMois   : {counts['charge_machine_mensuelle']}")
    print("=== Sprint 5 Lot 5a ===")
    print(f"OutilDecoupe        : {counts['outil_decoupe']}")
    print(f"\nTotal : {sum(counts.values())} lignes insérées.")


if __name__ == "__main__":
    main()
