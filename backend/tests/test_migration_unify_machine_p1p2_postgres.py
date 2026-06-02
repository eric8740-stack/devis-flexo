"""P1+P2 — test de migration SOUS FK STRICTES (Postgres uniquement).

Pourquoi ce test :
  - Les 2 autres tests `test_migration_unify_machine_p1p2.py::test_upgrade_*`
    sont skippes parce que SQLite ne peut pas appliquer FOREIGN_KEYS=ON pendant
    une transaction Alembic (cf docstring de ces tests). Or c'est PRECISEMENT
    le scenario du boot Railway prod : Postgres avec FK strict, qui rejette
    immediatement toute violation.
  - Ce test prouve, en faisant tourner la migration sur un Postgres reel,
    que :
      1. `op.drop_constraint(...)` AVANT l'UPDATE des FK leve les FK MI -> permet
         l'UPDATE remap.
      2. Les 3 machine_imprimerie sont inserees en `machine` (1 par MI).
      3. Les FK `lot_production.machine_id` + `porte_cliche.machine_id` sont
         remappees vers les nouveaux `machine.id` (et non plus `machine_imprimerie.id`).
      4. `op.create_foreign_key(...)` vers `machine` est cree apres l'UPDATE
         et accepte (donc le mapping est coherent).
      5. `machine_imprimerie` + `configuration_pose` sont droppees.
      6. ZERO IntegrityError tout au long du upgrade.

Conditions d'execution :
  - Variable d'env `PG_TEST_URL` (ex. postgresql://postgres:postgres@localhost:5432/postgres).
    Sans cette URL, le test est SKIPPE (vie locale Eric Windows sans Docker).
    En CI GitHub Actions backend.yml, l'URL est fournie par le service `postgres:16`.

Strategie d'isolation :
  - Le test cree une DB temporaire (`pgtest_p1p2_<random>`) dans le serveur
    pointe par PG_TEST_URL, applique la migration, vérifie, puis drop la DB.
    Aucun effet de bord sur la DB par défaut.

Note sequence migration (verifiee dans alembic/versions/b2c3d4e5f6g7_unify_machine_p1p2.py
ligne 165-194) :
  - Postgres : op.drop_constraint AVANT bloc UPDATE remap, op.create_foreign_key
    APRES. C'est l'ordre prouve par CE TEST.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from sqlalchemy import create_engine, text


PG_TEST_URL = os.getenv("PG_TEST_URL")
pytestmark = pytest.mark.skipif(
    not PG_TEST_URL,
    reason=(
        "PG_TEST_URL absent. Ce test exige un Postgres reel (FK strictes). "
        "Local : `PG_TEST_URL=postgresql://...` ; CI : service postgres:16 du "
        "workflow backend.yml."
    ),
)


REVISION_AVANT_P1P2 = "a1b2c3d4e5f6"  # B3b drop colonne vitesse_pratique_m_min
REVISION_P1P2 = "b2c3d4e5f6g7"        # head au moment de l'ecriture du test
BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _split_url_db(url: str) -> tuple[str, str]:
    """Separe la base server-only (sans dbname) du nom de la DB."""
    parsed = urlparse(url)
    dbname = parsed.path.lstrip("/") or "postgres"
    server_url = urlunparse(parsed._replace(path="/postgres"))
    return server_url, dbname


def _create_temp_db(server_url: str, dbname: str) -> None:
    """Cree une DB jetable. Postgres ne supporte pas CREATE DATABASE dans une
    transaction -> isolation_level AUTOCOMMIT."""
    engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    finally:
        engine.dispose()


def _drop_temp_db(server_url: str, dbname: str) -> None:
    engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            # Force la deconnexion des sessions residuelles avant DROP DATABASE
            # (sinon Postgres refuse avec "database is being accessed").
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ),
                {"db": dbname},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}"'))
    finally:
        engine.dispose()


def _resync_pg_sequences(db_url: str) -> None:
    """Bug Postgres classique : les migrations alembic data (Sprint 12+) font
    des `INSERT entreprise (id, ...) VALUES (1, ...)` sans bumper la sequence
    `entreprise_id_seq`. Resultat : la sequence reste a 1, et le prochain
    auto-increment du seed test collisionne avec 'entreprise_pkey'. Fix : on
    resync toutes les sequences avec MAX(id) post-upgrade. No-op si la table
    n'a pas de serial sequence sur 'id'.
    """
    # Whitelist explicite des tables touchees par le seed test. information_
    # schema.columns peut retourner des objets non-table (views) ou des tables
    # dont 'pg_get_serial_sequence' echoue avec UndefinedColumn meme si la
    # colonne id existe en theorie -> on prefere la liste blanche, defendable
    # et sans surprise.
    tables = (
        "entreprise",
        "machine",
        "machine_imprimerie",
        "cylindre_magnetique",
        "matiere",
        "devis",
        "lot_production",
        "porte_cliche",
    )
    engine = create_engine(db_url)
    try:
        with engine.begin() as conn:
            for table in tables:
                seq = conn.execute(
                    text("SELECT pg_get_serial_sequence(:t, 'id')"),
                    {"t": table},
                ).scalar()
                if seq is None:
                    continue
                conn.execute(
                    text(
                        f"SELECT setval(:seq, "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
                        f"(SELECT MAX(id) FROM {table}) IS NOT NULL)"
                    ),
                    {"seq": seq},
                )
    finally:
        engine.dispose()


def _run_alembic(db_url: str, *args: str) -> None:
    """Lance alembic en subprocess avec DATABASE_URL ecrasee. Subprocess pour
    isoler `app.db` qui resout DATABASE_URL au moment de l'import."""
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"alembic {' '.join(args)} a echoue (rc={result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


@pytest.fixture()
def fresh_pg_db():
    """Cree une DB Postgres jetable + yield son URL + cleanup."""
    assert PG_TEST_URL is not None  # garde-fou : skipif filtre en amont
    server_url, _ = _split_url_db(PG_TEST_URL)
    dbname = f"pgtest_p1p2_{secrets.token_hex(6)}"
    _create_temp_db(server_url, dbname)
    parsed = urlparse(PG_TEST_URL)
    test_url = urlunparse(parsed._replace(path=f"/{dbname}"))
    try:
        yield test_url
    finally:
        _drop_temp_db(server_url, dbname)


def _seed_etat_avant_p1p2(db_url: str) -> dict[str, int]:
    """Insere l'etat AVANT P1+P2 : 1 entreprise demo, 1 Machine seedee (Mark
    Andy P5), 3 MachineImprimerie catalogue, 1 lot_production + 1 porte_cliche
    pointant sur une MI. Retourne les ids cle pour assertions."""
    engine = create_engine(db_url)
    try:
        with engine.begin() as conn:
            ent_id = conn.execute(
                text(
                    "INSERT INTO entreprise "
                    "(raison_sociale, siret, email, is_demo) "
                    "VALUES ('Demo P1P2', '00000000000001', 'demo-p1p2@test.fr', "
                    "true) RETURNING id"
                )
            ).scalar()

            # Machine seedee Sprint 2 (presente AVANT P1+P2). On reproduit la
            # forme tenant demo : Mark Andy P5 laize 330.
            machine_p5_id = conn.execute(
                text(
                    "INSERT INTO machine "
                    "(entreprise_id, nom, laize_max_mm, laize_utile_mm, "
                    " vitesse_moyenne_m_h, nb_groupes_couleurs, "
                    " nb_postes_decoupe, actif) "
                    "VALUES (:eid, 'Mark Andy P5', 330, 330, 6000, 8, 1, true) "
                    "RETURNING id"
                ),
                {"eid": ent_id},
            ).scalar()

            # 3 machine_imprimerie catalogue (laizes specifiques par presse).
            mi_2200_id = conn.execute(
                text(
                    "INSERT INTO machine_imprimerie "
                    "(entreprise_id, nom, laize_totale_mm, laize_utile_mm, "
                    " nb_groupes_couleurs, nb_postes_decoupe, "
                    " vitesse_pratique_m_min, cout_horaire_eur, "
                    " options, actif, date_creation) "
                    "VALUES (:eid, 'Mark Andy 2200', 330, 320, 8, 1, 70, "
                    " 70.00, '[]'::json, true, CURRENT_TIMESTAMP) RETURNING id"
                ),
                {"eid": ent_id},
            ).scalar()
            mi_omet_id = conn.execute(
                text(
                    "INSERT INTO machine_imprimerie "
                    "(entreprise_id, nom, laize_totale_mm, laize_utile_mm, "
                    " nb_groupes_couleurs, nb_postes_decoupe, "
                    " vitesse_pratique_m_min, cout_horaire_eur, "
                    " options, actif, date_creation) "
                    "VALUES (:eid, 'OMET XFlex 330', 340, 330, 10, 2, 80, "
                    " 95.00, '[]'::json, true, CURRENT_TIMESTAMP) RETURNING id"
                ),
                {"eid": ent_id},
            ).scalar()
            mi_nilpeter_id = conn.execute(
                text(
                    "INSERT INTO machine_imprimerie "
                    "(entreprise_id, nom, laize_totale_mm, laize_utile_mm, "
                    " nb_groupes_couleurs, nb_postes_decoupe, "
                    " vitesse_pratique_m_min, cout_horaire_eur, "
                    " options, actif, date_creation) "
                    "VALUES (:eid, 'Nilpeter FA-22', 340, 330, 8, 2, 75, "
                    " 90.00, '[]'::json, true, CURRENT_TIMESTAMP) RETURNING id"
                ),
                {"eid": ent_id},
            ).scalar()

            # Cylindre + Matiere pour pouvoir poser un lot_production.
            cyl_id = conn.execute(
                text(
                    "INSERT INTO cylindre_magnetique "
                    "(entreprise_id, developpe_mm, actif) "
                    "VALUES (:eid, 96, true) RETURNING id"
                ),
                {"eid": ent_id},
            ).scalar()
            mat_id = conn.execute(
                text(
                    "INSERT INTO matiere "
                    "(entreprise_id, code, libelle, actif) "
                    "VALUES (:eid, 'TEST', 'matiere test', true) RETURNING id"
                ),
                {"eid": ent_id},
            ).scalar()

            # 1 devis (pour FK lot_production). date_creation server_default.
            devis_id = conn.execute(
                text(
                    "INSERT INTO devis "
                    "(entreprise_id, numero, statut, payload_input, "
                    " payload_output, mode_calcul, format_h_mm, format_l_mm, "
                    " machine_id, type_entree_fichier) "
                    "VALUES (:eid, 'DEV-2026-9999', 'brouillon', "
                    " '{\"placeholder\": true}'::json, "
                    " '{\"placeholder\": true}'::json, "
                    " 'cas1', 50, 100, :mid, 'a_designer') "
                    "RETURNING id"
                ),
                {"eid": ent_id, "mid": machine_p5_id},
            ).scalar()

            # lot_production : entreprise_id NOT NULL + colonne 'ordre' (pas
            # ordre_lot). machine_id pointe sur MI 2200 -> FK machine_imprimerie.id.
            lot_id = conn.execute(
                text(
                    "INSERT INTO lot_production "
                    "(devis_id, entreprise_id, machine_id, cylindre_id, "
                    " matiere_id, nb_poses_dev, nb_poses_laize, "
                    " sens_enroulement, quantite, ordre) "
                    "VALUES (:did, :eid, :mid, :cid, :matid, 2, 3, 1, 10000, 1) "
                    "RETURNING id"
                ),
                {
                    "did": devis_id,
                    "eid": ent_id,
                    "mid": mi_2200_id,
                    "cid": cyl_id,
                    "matid": mat_id,
                },
            ).scalar()

            # porte_cliche : colonne 'quantite' (pas nb_couleurs).
            # machine_id pointe sur MI OMET.
            pc_id = conn.execute(
                text(
                    "INSERT INTO porte_cliche "
                    "(entreprise_id, cylindre_id, machine_id, quantite) "
                    "VALUES (:eid, :cid, :mid, 4) "
                    "RETURNING id"
                ),
                {"eid": ent_id, "cid": cyl_id, "mid": mi_omet_id},
            ).scalar()

            return {
                "ent_id": ent_id,
                "machine_p5_id": machine_p5_id,
                "mi_2200_id": mi_2200_id,
                "mi_omet_id": mi_omet_id,
                "mi_nilpeter_id": mi_nilpeter_id,
                "devis_id": devis_id,
                "lot_id": lot_id,
                "pc_id": pc_id,
            }
    finally:
        engine.dispose()


def test_migration_p1p2_sous_fk_strictes_postgres(fresh_pg_db):
    """E2E migration P1+P2 sur Postgres FK strict.

    Sequence :
      1. alembic upgrade jusqu'a la rev AVANT P1+P2 (a1b2c3d4e5f6).
      2. Seed l'etat legacy : 1 entreprise + 1 Machine seedee + 3 MI catalogue
         + 1 lot_production pointant sur MI + 1 porte_cliche pointant sur MI.
      3. alembic upgrade head (applique P1+P2 b2c3d4e5f6g7).
      4. Assertions :
         - 4 Machine au total (P5 + 3 inserees depuis MI).
         - lot_production.machine_id = id de Machine 'Mark Andy 2200' (et plus
           l'ancien mi_2200_id).
         - porte_cliche.machine_id = id de Machine 'OMET XFlex 330'.
         - Tables machine_imprimerie + configuration_pose DROPPEES.
         - Laizes preservees (value-neutral) : Mark Andy 2200 laize_utile=320.

    Tout au long de l'upgrade : aucune IntegrityError (sinon subprocess
    alembic rc != 0 et _run_alembic leve AssertionError immediatement).
    """
    db_url = fresh_pg_db

    # 1. Migrate to rev AVANT P1+P2
    _run_alembic(db_url, "upgrade", REVISION_AVANT_P1P2)

    # 1bis. Resync sequences Postgres : les migrations data Sprint 12+ INSERT
    # avec id explicite sans bump de seq -> sinon UniqueViolation au seed.
    _resync_pg_sequences(db_url)

    # 2. Seed etat legacy avec FK strictes (Postgres natif)
    ids = _seed_etat_avant_p1p2(db_url)

    # 3. Apply P1+P2 (en CE TEST, on observe d'eventuelles violations FK)
    _run_alembic(db_url, "upgrade", "head")

    # 4. Asserts post-migration (FILTRES SUR MON tenant test : les migrations
    # data Sprint 12+ peuvent avoir seede d'autres entreprises avec leurs
    # propres machines -- on isole MON entreprise test pour la verification).
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            # 4 Machine pour mon tenant (P5 + Mark Andy 2200 + OMET + Nilpeter)
            machines = conn.execute(
                text(
                    "SELECT id, nom, laize_utile_mm FROM machine "
                    "WHERE entreprise_id = :eid ORDER BY id"
                ),
                {"eid": ids["ent_id"]},
            ).fetchall()
            noms = [m.nom for m in machines]
            assert len(machines) == 4, (
                f"Attendu 4 Machine post-migration pour tenant test "
                f"(entreprise_id={ids['ent_id']}), recu {len(machines)} : {noms}"
            )
            assert "Mark Andy P5" in noms, "Machine seedee P5 perdue"
            assert "Mark Andy 2200" in noms, "MI 2200 non re-insere en Machine"
            assert "OMET XFlex 330" in noms, "MI OMET non re-insere en Machine"
            assert "Nilpeter FA-22" in noms, "MI Nilpeter non re-insere en Machine"

            # Laizes preservees (VALUE-NEUTRAL)
            laizes = {m.nom: float(m.laize_utile_mm) for m in machines}
            assert laizes["Mark Andy 2200"] == 320.0, (
                f"Mark Andy 2200 laize_utile devrait etre 320 (preserve tripwire "
                f"P0b 704,07), recu {laizes['Mark Andy 2200']}"
            )
            assert laizes["OMET XFlex 330"] == 330.0
            assert laizes["Nilpeter FA-22"] == 330.0

            # FK lot_production remappee vers machine.id (Mark Andy 2200)
            new_machine_2200_id = next(
                m.id for m in machines if m.nom == "Mark Andy 2200"
            )
            lot_machine_id = conn.execute(
                text("SELECT machine_id FROM lot_production WHERE id = :id"),
                {"id": ids["lot_id"]},
            ).scalar()
            assert lot_machine_id == new_machine_2200_id, (
                f"lot_production.machine_id devrait pointer sur la nouvelle "
                f"Machine 'Mark Andy 2200' (id={new_machine_2200_id}), "
                f"recu {lot_machine_id} (= ancien mi_2200_id={ids['mi_2200_id']} ?)"
            )

            # FK porte_cliche remappee vers machine.id (OMET)
            new_machine_omet_id = next(
                m.id for m in machines if m.nom == "OMET XFlex 330"
            )
            pc_machine_id = conn.execute(
                text("SELECT machine_id FROM porte_cliche WHERE id = :id"),
                {"id": ids["pc_id"]},
            ).scalar()
            assert pc_machine_id == new_machine_omet_id, (
                f"porte_cliche.machine_id devrait pointer sur la nouvelle "
                f"Machine 'OMET XFlex 330' (id={new_machine_omet_id}), "
                f"recu {pc_machine_id}"
            )

            # Tables MI + configuration_pose DROPPEES
            tables = {
                r.tablename
                for r in conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public'"
                    )
                ).fetchall()
            }
            assert "machine_imprimerie" not in tables, (
                "machine_imprimerie devrait etre droppee post-P1+P2"
            )
            assert "configuration_pose" not in tables, (
                "configuration_pose devrait etre droppee post-P1+P2"
            )

            # FK active sur lot_production.machine_id vers machine.id
            fk_target = conn.execute(
                text(
                    "SELECT confrelid::regclass::text AS target_table "
                    "FROM pg_constraint "
                    "WHERE conname = 'lot_production_machine_id_fkey'"
                )
            ).scalar()
            assert fk_target == "machine", (
                f"FK lot_production_machine_id_fkey devrait viser 'machine', "
                f"recu {fk_target}"
            )
            fk_target_pc = conn.execute(
                text(
                    "SELECT confrelid::regclass::text AS target_table "
                    "FROM pg_constraint "
                    "WHERE conname = 'porte_cliche_machine_id_fkey'"
                )
            ).scalar()
            assert fk_target_pc == "machine", (
                f"FK porte_cliche_machine_id_fkey devrait viser 'machine', "
                f"recu {fk_target_pc}"
            )
    finally:
        engine.dispose()
