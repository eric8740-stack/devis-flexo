"""Peuple la base depuis les CSV de backend/seeds/.

Stratégie : DELETE **scopé tenant démo** puis INSERT (idempotent —
relançable à l'infini). Robuste à l'encodage (UTF-8 ou UTF-8-BOM) et au
séparateur (, ou ;). Cellules vides → None en base.

Blindage pilote (audit 05/07/2026, C1) — l'app est MULTI-TENANT :
- Tous les DELETE sont scopés sur l'entreprise démo (DEMO_ENTREPRISE_ID).
  Un re-seed ne touche JAMAIS les données des autres tenants.
- Garde-fou Postgres : si la base cible est PostgreSQL (= prod Railway),
  le seed REFUSE de tourner sauf flag explicite `--force-prod` ou variable
  d'environnement `SEED_CONFIRM_PROD=oui`.
- Sur PostgreSQL, `ADMIN_INITIAL_PASSWORD` est OBLIGATOIRE (pas de compte
  admin/« admin » silencieux en prod).

Usage (depuis backend/, venv activé) :

    python -m scripts.seed                # dev SQLite
    python -m scripts.seed --force-prod   # prod Postgres (assumé)
"""
from __future__ import annotations

import csv
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Catalogue,
    ChargeMachineMensuelle,
    ChargeMensuelle,
    Client,
    Complexe,
    ConfigChangements,
    ConfigCouts,
    ConfigRoulage,
    CorrespondanceLaizeMetrage,
    Devis,
    Entreprise,
    Fournisseur,
    Machine,
    OperationFinition,
    OutilDecoupe,
    PartenaireST,
    TarifEncre,
    TarifPoste,
    TempsOperationStandard,
    User,
)

# Sprint 12 multi-tenant — id de l'entreprise demo (Paysant & Fils Étiquettes).
# Tous les records seedés sont rattachés à ce tenant.
DEMO_ENTREPRISE_ID = 1

# Sprint 12 multi-tenant — context bcrypt partagé pour le seed du compte admin.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"


# ---------------------------------------------------------------------------
# Garde-fous prod (audit 05/07/2026 — C1 + E3)
# ---------------------------------------------------------------------------


def _verifier_garde_fou_postgres(dialect_name: str, force: bool) -> None:
    """Refuse de seeder une base PostgreSQL sans confirmation explicite.

    PostgreSQL = prod Railway (le dev local et les tests sont sur SQLite).
    Le seed reste destructif POUR LE TENANT DÉMO (DELETE scopés) : on exige
    donc un acte volontaire avant de toucher la prod. Deux déverrouillages
    possibles : argument CLI `--force-prod` ou env `SEED_CONFIRM_PROD=oui`.
    """
    if dialect_name != "postgresql":
        return
    if force or os.getenv("SEED_CONFIRM_PROD", "").strip().lower() == "oui":
        logger.warning(
            "Seed sur PostgreSQL confirmé (--force-prod / SEED_CONFIRM_PROD). "
            "Seules les données du tenant démo (entreprise_id=%s) seront "
            "réécrites.",
            DEMO_ENTREPRISE_ID,
        )
        return
    raise SystemExit(
        "REFUS : la base cible est PostgreSQL (prod Railway ?). Le seed "
        "réécrit les données du tenant démo (DELETE + INSERT scopés "
        f"entreprise_id={DEMO_ENTREPRISE_ID}). Pour confirmer en toute "
        "connaissance de cause : relancer avec `--force-prod` ou définir "
        "SEED_CONFIRM_PROD=oui. Les autres tenants ne sont jamais touchés."
    )


def _resoudre_admin_password(dialect_name: str) -> str:
    """Password du compte admin démo — fail-fast en prod (audit E3).

    Sur PostgreSQL (prod), `ADMIN_INITIAL_PASSWORD` est obligatoire : on
    refuse de créer silencieusement un compte admin/« admin » exposé sur
    Internet. En dev SQLite, fallback "admin" conservé (avec WARNING).
    """
    admin_password = os.getenv("ADMIN_INITIAL_PASSWORD")
    if admin_password:
        return admin_password
    if dialect_name == "postgresql":
        raise SystemExit(
            "REFUS : ADMIN_INITIAL_PASSWORD absent alors que la base cible "
            "est PostgreSQL (prod). Définir la variable (Railway ou shell) "
            "avant de relancer le seed — pas de mot de passe admin par "
            "défaut en production."
        )
    logger.warning(
        "ADMIN_INITIAL_PASSWORD not set — using fallback 'admin'. "
        "CHANGE IN PRODUCTION via Railway env var."
    )
    return "admin"


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


def _to_json_list(value: str | None) -> list[str] | None:
    # CSV → liste JSON pour colonnes JSON (certifications). Cellule vide → None.
    # Plusieurs valeurs séparées par ';' (le ',' est le séparateur CSV).
    if not value or not value.strip():
        return None
    return [item.strip() for item in value.split(";") if item.strip()]


# ---------------------------------------------------------------------------
# Sprint 0-1 : entreprise / client / fournisseur
# ---------------------------------------------------------------------------


def seed_entreprise(session: Session) -> int:
    """UPSERT de l'entreprise démo (audit C1 — plus de DELETE global).

    Avant : `session.query(Entreprise).delete()` supprimait TOUTES les
    entreprises (multi-tenant → destruction des autres comptes + cascade
    users/clients/devis). Désormais : UPDATE si la row du CSV existe déjà
    (par id), INSERT sinon. Le compte admin démo et ses sessions JWT
    survivent au re-seed (cf. seed_user_admin, idempotent par UPDATE).
    """
    rows = read_csv_rows(SEEDS_DIR / "entreprise.csv")
    for row in rows:
        valeurs = dict(
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
            # Sprint 12 multi-tenant — Paysant & Fils est l'entreprise demo
            # qui hérite des 148 records seedés (Eric admin)
            is_demo=True,
        )
        existing = session.get(Entreprise, _to_int(row["id"]))
        if existing is not None:
            for champ, valeur in valeurs.items():
                setattr(existing, champ, valeur)
        else:
            session.add(Entreprise(id=_to_int(row["id"]), **valeurs))
    return len(rows)


def seed_user_admin(session: Session) -> int:
    """Sprint 12 multi-tenant — crée/UPDATE le compte admin Eric (demo).

    Lié à l'entreprise demo (DEMO_ENTREPRISE_ID, Paysant & Fils).
    Password lu depuis `ADMIN_INITIAL_PASSWORD` env var. Audit 05/07/2026
    (E3) : sur PostgreSQL (prod), la variable est OBLIGATOIRE — le seed
    s'arrête sinon. En dev SQLite : fallback "admin" avec WARNING.

    is_active=True (skip confirmation email pour ce compte créé via seed).
    is_admin=True (accès aux endpoints /api/admin).

    Idempotent : si un user existe déjà pour entreprise_id=1, on UPDATE
    le hash et l'email au lieu d'INSERT (préserve l'id et les sessions
    JWT actives entre re-seeds).
    """
    admin_email = os.getenv("ADMIN_INITIAL_EMAIL", "admin@devis-flexo.fr")
    admin_password = _resoudre_admin_password(session.bind.dialect.name)
    password_hash = _pwd_context.hash(admin_password)

    existing = (
        session.query(User)
        .filter(User.entreprise_id == DEMO_ENTREPRISE_ID)
        .first()
    )
    if existing is not None:
        existing.email = admin_email
        existing.password_hash = password_hash
        existing.is_active = True
        existing.is_admin = True
        existing.nom_contact = "Eric Paysant"
        # Sprint 13 Lot S13.A — Eric admin = bundle FlexoSuite complet.
        # Explicité ici (en plus du default modèle) pour que le re-seed
        # remette les flags à True si jamais ils ont été désactivés en
        # debug. Garantit l'accès Eric à tous les modules pour le support.
        existing.has_flexocompare = True
        existing.has_flexocheck = True
        return 1

    session.add(
        User(
            email=admin_email,
            password_hash=password_hash,
            nom_contact="Eric Paysant",
            entreprise_id=DEMO_ENTREPRISE_ID,
            is_active=True,
            is_admin=True,
            # Sprint 13 Lot S13.A — bundle FlexoSuite à la création.
            has_flexocompare=True,
            has_flexocheck=True,
        )
    )
    return 1


def seed_client(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "client.csv")
    # Audit C1 — DELETE scopé tenant démo (jamais les clients des autres).
    session.query(Client).filter(
        Client.entreprise_id == DEMO_ENTREPRISE_ID
    ).delete()
    for row in rows:
        session.add(
            Client(
                id=_to_int(row["id"]),
                entreprise_id=DEMO_ENTREPRISE_ID,
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
    # Audit C1 — DELETE scopé tenant démo.
    session.query(Fournisseur).filter(
        Fournisseur.entreprise_id == DEMO_ENTREPRISE_ID
    ).delete()
    for row in rows:
        session.add(
            Fournisseur(
                id=_to_int(row["id"]),
                entreprise_id=DEMO_ENTREPRISE_ID,
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
        # B1 — derivation transitoire pour le tenant demo : laize_utile :=
        # laize_max. nb_postes_decoupe a 1 et options a [] par defaut
        # (server_default). A affiner via UI B2.
        # B3b : `vitesse_pratique_m_min` retire (colonne droppee, le moteur
        # derive `vitesse_moyenne_m_h / 60` a la volee).
        laize_max_val = _to_float(row.get("laize_max_mm"))
        session.add(
            Machine(
                id=_to_int(row["id"]),
                entreprise_id=DEMO_ENTREPRISE_ID,
                nom=row["nom"],
                largeur_max_mm=_to_int(row.get("largeur_max_mm")),
                laize_max_mm=laize_max_val,
                vitesse_max_m_min=_to_int(row.get("vitesse_max_m_min")),
                nb_groupes_couleurs=_to_int(row.get("nb_groupes_couleurs")),
                cout_horaire_eur=_to_float(row.get("cout_horaire_eur")),
                vitesse_moyenne_m_h=_to_int(row.get("vitesse_moyenne_m_h")),
                duree_calage_h=_to_float(row.get("duree_calage_h")),
                laize_utile_mm=laize_max_val,
                actif=actif,
                commentaire=row.get("commentaire"),
                # #4.3 — rôle : presse (défaut) / finition. Daco D250 =
                # finition (cf machine.csv) → exclue des candidats optim.
                type_machine=row.get("type_machine") or "presse",
            )
        )
    return len(rows)


def seed_operation_finition(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "operation_finition.csv")
    for row in rows:
        session.add(
            OperationFinition(
                id=_to_int(row["id"]),
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
                reference=row["reference"],
                famille=row["famille"],
                face_matiere=row.get("face_matiere"),
                # Lot 1 complexe enrichi : grammage Numeric (films décimaux).
                grammage_g_m2=_to_float(row.get("grammage_g_m2")),
                adhesif_type=row.get("adhesif_type"),
                prix_m2_eur=_to_float(row["prix_m2_eur"]),
                fournisseur_id=_to_int(row.get("fournisseur_id")),
                actif=actif,
                commentaire=row.get("commentaire"),
                # Lot 1 complexe enrichi — champs optim + certifs.
                epaisseur_microns=_to_int(row.get("epaisseur_microns")),
                est_transparent=_to_bool(row.get("est_transparent")),
                opacite_pct=_to_float(row.get("opacite_pct")),
                sous_type=row.get("sous_type") or None,
                certifications_sanitaires=_to_json_list(
                    row.get("certifications_sanitaires")
                ),
                certifications_env=_to_json_list(row.get("certifications_env")),
            )
        )
    return len(rows)


def seed_config_strategique(session: Session) -> int:
    """Brief stratégique v2 Phase 1 — config template NEUTRE du tenant démo.

    Valeurs par défaut neutres (cf. brief section IV) : chaque entreprise les
    ajuste ensuite via l'onglet Stratégique. Singletons couts/changements +
    2 formats roulage d'exemple. Pas de données ICE ici (ICE → fixtures test).
    """
    session.add(
        ConfigCouts(
            entreprise_id=DEMO_ENTREPRISE_ID,
            # Phase 2 Lot 3 — alignement legacy : P5 Roulage et P7 MO basculent
            # sur ConfigCouts (au lieu des TarifPoste roulage_prix_horaire=375
            # et mo_prix_horaire=70 € dépréciés). Le seed démo reflète ces
            # valeurs ICE historiques pour préserver V1a 1 449,09 €. Les
            # défauts template du modèle (50/25) restent appliqués aux
            # nouveaux tenants (onboarding).
            cout_exploitation_machine_eur_h=375.0,
            cout_operateur_eur_h=70.0,
            cout_energies_eur_h=3.5,
            cout_fixe_atelier_eur_mois=2500.0,
            cout_fixe_maintenance_eur_mois=800.0,
            # Phase 2 Lot 2 — alignement legacy : la marge du tenant démo passe
            # de 35 % (template neutre par défaut) à 18 %, valeur historique
            # ICE de `Entreprise.pct_marge_defaut`.
            marge_standard_pct=18.0,
            buffer_rebut_pct=2.5,
            buffer_setup_pct=1.0,
            # Phase 2 Lot 4a — alignement legacy P1/P3/P4/P6 (anciens
            # TarifPoste marge_confort_roulage_mm=10, cliche_prix_couleur=45,
            # outil_base_eur=200, outil_par_trace_eur=50,
            # surcout_forme_speciale_pct=1.40, calage_forfait=225,
            # finitions_prix_m2=0.1250). Préserve V1a 1 449,09 € et les
            # autres sacrés du benchmark. Defaults template du modèle
            # (10/30/150/40/1.30/180/0.10) restent actifs aux nouveaux tenants.
            marge_confort_roulage_mm=10,
            cliche_prix_couleur_eur=45.0,
            outil_base_eur=200.0,
            outil_par_trace_eur=50.0,
            surcout_forme_speciale_facteur=1.40,
            calage_forfait_eur=225.0,
            finitions_prix_m2_eur=0.1250,
        )
    )
    session.add(
        ConfigChangements(
            entreprise_id=DEMO_ENTREPRISE_ID,
            changement_couleur_duree_min=15,
            changement_couleur_cout_eur=12.5,
            changement_format_duree_min=25,
            changement_format_cout_eur=18.0,
            nettoyage_duree_min=45,
            nettoyage_cout_eur=35.0,
        )
    )
    roulages = [
        ("A5", 280, "helicoidal", 3.0),
        ("A4", 250, "alterne", 5.0),
    ]
    for fmt, debit, mode, rebut in roulages:
        session.add(
            ConfigRoulage(
                entreprise_id=DEMO_ENTREPRISE_ID,
                format_libelle=fmt,
                debit_mm_s=debit,
                mode_roulage=mode,
                rebut_pct=rebut,
            )
        )
    return 2 + len(roulages)


def seed_catalogue(session: Session) -> int:
    rows = read_csv_rows(SEEDS_DIR / "catalogue.csv")
    for row in rows:
        session.add(
            Catalogue(
                id=_to_int(row["id"]),
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
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
                entreprise_id=DEMO_ENTREPRISE_ID,
                mois=_to_int(row["mois"]),
                annee=_to_int(row["annee"]),
                montant_total=_to_float(row["montant_total"]),
                heures_disponibles=_to_float(row["heures_disponibles"]),
                source=row.get("source"),
            )
        )
    return len(rows)


# ---------------------------------------------------------------------------
# Sync séquences Postgres (mini-sprint Note 16 — 04/05/2026)
# ---------------------------------------------------------------------------


# Tables seedées avec un id auto-increment forcé par le CSV.
# `devis` n'est PAS dans la liste : créée au runtime via POST /api/devis,
# sa séquence est gérée naturellement par Postgres.
_TABLES_WITH_SERIAL_ID = [
    "entreprise",
    "client",
    "fournisseur",
    "machine",
    "complexe",
    "catalogue",
    "operation_finition",
    "partenaire_st",
    "charge_mensuelle",
    "charge_machine_mensuelle",
    "correspondance_laize_metrage",
    "tarif_encre",
    "tarif_poste",
    "temps_operation_standard",
    "outil_decoupe",
    # Sprint 12 multi-tenant — table user créée via seed_user_admin
    "user",
]


def _reset_postgres_sequences(session: Session) -> None:
    """Synchronise les séquences Postgres après un seed avec ids forcés.

    Mini-sprint Note 16 (04/05/2026) — résorption d'un bug latent depuis
    Sprint 2/3, exposé par Sprint 9 v2 UI outils. PostgreSQL ne
    synchronise pas la séquence auto-increment lorsqu'un INSERT spécifie
    explicitement l'id. Conséquence : tout POST suivant sans id explicite
    tente `nextval() = 1` et collisionne avec une ligne existante → 409.

    Pour chaque table, on remet la séquence à `MAX(id)` avec `is_called`
    selon l'état :
      - table non vide : `setval(seq, MAX(id), TRUE)` → next nextval = MAX+1
      - table vide     : `setval(seq, 1, FALSE)`     → next nextval = 1

    No-op sur SQLite (pas de séquence explicite, ROWID est un alias d'id
    qui se réaligne automatiquement sur MAX+1).
    """
    if session.bind.dialect.name != "postgresql":
        return

    for table_name in _TABLES_WITH_SERIAL_ID:
        sequence_name = f"{table_name}_id_seq"
        sql = (
            f"SELECT setval("
            f"'{sequence_name}', "
            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), "
            f"(SELECT COUNT(*) FROM {table_name}) > 0)"
        )
        session.execute(text(sql))
    session.commit()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def modeles_purge_ordonnes() -> tuple:
    """Tables seedées, dans l'ordre FK-safe de suppression.

    Enfants (lots, devis, catalogue, complexe) AVANT parents (client,
    fournisseur, machine) pour éviter les violations FK (devis.machine_id
    NOT NULL FK, devis.client_id SET NULL, catalogue.client_id RESTRICT,
    complexe.fournisseur_id SET NULL, catalogue.machine_id SET NULL).

    Sprint 4 (devis) en TÊTE car FK NOT NULL vers machine (Note 15).
    P1+P2 : LotProduction + PorteCliche aussi en TÊTE car post-fusion
    MI -> Machine, leurs FK machine_id pointent vers machine.id
    (cf migration b2c3d4e5f6g7). Sans ce DELETE, DELETE FROM machine
    echoue avec FOREIGN KEY constraint failed des qu'un lot/PC existe.

    Réutilisé par tests/conftest.py (wipe global de la base de test).
    """
    from app.models import LotProduction, PorteCliche

    return (
        LotProduction,
        PorteCliche,
        Devis,
        Catalogue,
        Complexe,
        Machine,
        OperationFinition,
        PartenaireST,
        ChargeMensuelle,
        # Tables S3 Lot 3b — pas de FK entre elles ni vers les autres,
        # ordre libre. Groupées ici pour visibilité.
        TarifPoste,
        TarifEncre,
        TempsOperationStandard,
        ChargeMachineMensuelle,
        # S5
        OutilDecoupe,
        # Brief stratégique v2 Phase 1 — config par entreprise (FK entreprise)
        ConfigRoulage,
        ConfigChangements,
        ConfigCouts,
        # Sprint 0-1 — parents (déplacés ici depuis seed_client /
        # seed_fournisseur pour centraliser le scope tenant).
        Client,
        Fournisseur,
    )


def purge_tenant(session: Session, entreprise_id: int) -> None:
    """DELETE descendant des données d'UN tenant (audit C1 — scopé).

    Ne touche NI la table `entreprise` NI la table `user` (le compte admin
    démo survit au re-seed — cf. seed_user_admin, idempotent par UPDATE).
    `correspondance_laize_metrage` (référentiel GLOBAL sans entreprise_id)
    est gérée à part dans run_seed.
    """
    for modele in modeles_purge_ordonnes():
        session.query(modele).filter(
            modele.entreprise_id == entreprise_id
        ).delete(synchronize_session=False)


def run_seed(force_prod: bool = False) -> dict[str, int]:
    """Exécute tous les seeders dans une seule transaction.

    Ordre :
    1. DELETE descendant SCOPÉ TENANT DÉMO via `purge_tenant` (audit C1 —
       les autres tenants ne sont jamais touchés).
    2. INSERT ascendant via les fonctions seed_xxx + `session.flush()`
       après chaque table pour rendre les parents visibles aux enfants.
       Sans flush, SQLAlchemy n'ordonne pas correctement les INSERTs
       quand les FK sont déclarées sans `relationship()` → PostgreSQL
       refuse l'INSERT enfant car le parent n'est pas encore en base
       (ForeignKeyViolation). SQLite est plus laxiste et accepte.

    Garde-fou : si la base cible est PostgreSQL (prod Railway), refus
    sauf `force_prod=True` (CLI --force-prod) ou SEED_CONFIRM_PROD=oui.

    Mini-sprint Note 15 (04/05/2026) : `Devis` en tête de la purge.
    Conséquence assumée : tout re-seed wipe les devis DU TENANT DÉMO
    (acceptable en mode démo — les devis des autres tenants survivent).
    """
    counts: dict[str, int] = {}
    with SessionLocal() as session:
        _verifier_garde_fou_postgres(session.bind.dialect.name, force_prod)

        # Phase 1 — DELETE descendant scopé tenant démo (audit C1).
        purge_tenant(session, DEMO_ENTREPRISE_ID)
        # Référentiel GLOBAL sans entreprise_id (non exposé par l'API,
        # cf. évaluation M3 audit 05/07/2026) : re-seed complet assumé.
        session.query(CorrespondanceLaizeMetrage).delete(
            synchronize_session=False
        )
        session.flush()  # commit logique des DELETE en transaction

        # Phase 2 — INSERT ascendant + flush entre chaque pour respecter FK
        # Sprint 12 multi-tenant : entreprise + user_admin sont insérés en
        # premier car les 13 autres seeds ont une FK NOT NULL entreprise_id
        # vers entreprise.id (= DEMO_ENTREPRISE_ID = 1).
        for name, fn in (
            ("entreprise", seed_entreprise),
            ("user_admin", seed_user_admin),  # Sprint 12 — admin Eric
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
            # Brief stratégique v2 Phase 1 — config template neutre par tenant
            ("config_strategique", seed_config_strategique),
        ):
            counts[name] = fn(session)
            session.flush()

        session.commit()
        # Phase 3 — sync séquences Postgres après ids forcés (Note 16)
        _reset_postgres_sequences(session)
    return counts


def main() -> None:
    # Audit C1 — `--force-prod` : seul déverrouillage CLI du garde-fou
    # PostgreSQL (équivalent : SEED_CONFIRM_PROD=oui).
    force_prod = "--force-prod" in sys.argv[1:]
    counts = run_seed(force_prod=force_prod)
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
    print("=== Sprint 12 multi-tenant ===")
    print(f"User admin (demo)   : {counts['user_admin']}")
    print(f"\nTotal : {sum(counts.values())} lignes insérées.")


if __name__ == "__main__":
    main()
