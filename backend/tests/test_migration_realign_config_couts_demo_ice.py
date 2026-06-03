"""Test migration `c4d5e6f7a8b9_realign_config_couts_demo_ice`.

Verrou anti-régression du fix data prod : la ligne `config_couts` du compte
démo (entreprise_id=1) restée aux defaults template (35/50/25) sur une DB
PROD pré-existante est ré-alignée sur les valeurs ICE sacrées (18/375/70)
qui préservent V1a 1 449,09 €.

Couvre :
  - upgrade : entreprise_id=1 passe de 35/50/25 -> 18/375/70.
  - isolation multi-tenant STRICTE : un autre tenant (entreprise_id=2) avec
    ses propres coûts n'est PAS touché.
  - idempotence : downgrade (no-op) puis re-upgrade -> mêmes valeurs.

Scope EXCLUSIF tests/ sur DB SQLite éphémère — ne touche ni la dev DB ni le
seed démo. Implémentation : alembic via subprocess (DATABASE_URL override),
même pattern que test_migration_unify_machine_p1p2.py (env.py importe
app.db.engine au top-level → forcer l'URL avant import).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa


_BACKEND_DIR = Path(__file__).resolve().parent.parent

# Révision juste AVANT le fix (head P1+P2) et la révision du fix.
_REV_AVANT = "b2c3d4e5f6g7"
_REV_FIX = "c4d5e6f7a8b9"


def _run_alembic(db_url: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": db_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        env=env,
        cwd=str(_BACKEND_DIR),
        capture_output=True,
        text=True,
    )


def _upgrade(db_url: str, rev: str) -> None:
    r = _run_alembic(db_url, "upgrade", rev)
    assert r.returncode == 0, (
        f"alembic upgrade {rev} failed.\nstdout: {r.stdout}\nstderr: {r.stderr}"
    )


def _downgrade(db_url: str, rev: str) -> None:
    r = _run_alembic(db_url, "downgrade", rev)
    assert r.returncode == 0, (
        f"alembic downgrade {rev} failed.\nstdout: {r.stdout}\nstderr: {r.stderr}"
    )


@pytest.fixture
def db_url(tmp_path):
    db_file = tmp_path / "test_realign_config_couts.sqlite"
    return f"sqlite:///{db_file}"


def _seed_config_couts_pre_fix(engine: sa.engine.Engine) -> None:
    """Seed un état PROD pré-fix :
      - entreprise_id=1 (démo) avec config_couts aux DEFAULTS erronés 35/50/25.
        L'entreprise id=1 est DÉJÀ créée par les migrations (seed démo) à la
        révision b2c3d4e5f6g7 ; on n'insère donc QUE sa config_couts (la table
        config_couts, elle, reste vide en migration -> d'où le bug prod).
      - entreprise_id=2 (autre tenant) avec ses PROPRES coûts -> ne doit PAS
        bouger (isolation multi-tenant). Cette entreprise n'existe pas en
        migration : on la crée.
    Les colonnes Phase 1 de config_couts sont NOT NULL sans server_default :
    on les fournit toutes explicitement. Les 7 colonnes Lot 4a ont un
    server_default -> omises.
    """
    with engine.begin() as conn:
        # entreprise_id=1 existe déjà (migration seed démo) ; on crée seulement
        # le tenant témoin id=2.
        conn.execute(sa.text(
            "INSERT INTO entreprise (id, raison_sociale, siret) VALUES "
            "(2, 'Autre Imprimeur', '00000000000002')"
        ))
        # Tenant démo (1) : defaults template erronés (le bug prod).
        conn.execute(sa.text("""
            INSERT INTO config_couts (
                entreprise_id, cout_exploitation_machine_eur_h,
                cout_operateur_eur_h, cout_energies_eur_h,
                cout_fixe_atelier_eur_mois, cout_fixe_maintenance_eur_mois,
                marge_standard_pct, buffer_rebut_pct, buffer_setup_pct
            ) VALUES (
                1, 50, 25, 3.5, 2500, 800, 35, 2.5, 1.0
            )
        """))
        # Autre tenant (2) : valeurs propres distinctes -> témoin d'isolation.
        conn.execute(sa.text("""
            INSERT INTO config_couts (
                entreprise_id, cout_exploitation_machine_eur_h,
                cout_operateur_eur_h, cout_energies_eur_h,
                cout_fixe_atelier_eur_mois, cout_fixe_maintenance_eur_mois,
                marge_standard_pct, buffer_rebut_pct, buffer_setup_pct
            ) VALUES (
                2, 99, 42, 4.0, 3000, 900, 27, 3.0, 1.5
            )
        """))


def _lire_config(conn, entreprise_id: int):
    return conn.execute(sa.text(
        "SELECT marge_standard_pct, cout_exploitation_machine_eur_h, "
        "cout_operateur_eur_h FROM config_couts WHERE entreprise_id=:eid"
    ), {"eid": entreprise_id}).first()


def test_realign_demo_et_isolation_autre_tenant(db_url):
    """upgrade : ent=1 ré-aligné ICE (18/375/70), ent=2 intact."""
    _upgrade(db_url, _REV_AVANT)
    engine = sa.create_engine(db_url)
    _seed_config_couts_pre_fix(engine)

    _upgrade(db_url, _REV_FIX)

    with engine.begin() as conn:
        demo = _lire_config(conn, 1)
        assert float(demo.marge_standard_pct) == 18.0
        assert float(demo.cout_exploitation_machine_eur_h) == 375.0
        assert float(demo.cout_operateur_eur_h) == 70.0

        # Isolation multi-tenant : l'autre tenant garde ses valeurs propres.
        autre = _lire_config(conn, 2)
        assert float(autre.marge_standard_pct) == 27.0
        assert float(autre.cout_exploitation_machine_eur_h) == 99.0
        assert float(autre.cout_operateur_eur_h) == 42.0


def test_idempotence_downgrade_noop_puis_reupgrade(db_url):
    """downgrade (no-op volontaire) ne défait pas l'ICE ; re-upgrade = stable."""
    _upgrade(db_url, _REV_AVANT)
    engine = sa.create_engine(db_url)
    _seed_config_couts_pre_fix(engine)

    _upgrade(db_url, _REV_FIX)
    # downgrade -1 : la fonction downgrade() est un `pass` -> les données ICE
    # restent en place (on ne réintroduit jamais les defaults erronés).
    _downgrade(db_url, _REV_AVANT)
    with engine.begin() as conn:
        demo = _lire_config(conn, 1)
        assert float(demo.marge_standard_pct) == 18.0
        assert float(demo.cout_exploitation_machine_eur_h) == 375.0
        assert float(demo.cout_operateur_eur_h) == 70.0

    # re-upgrade : UPDATE re-appliqué -> mêmes valeurs (idempotent).
    _upgrade(db_url, _REV_FIX)
    with engine.begin() as conn:
        demo = _lire_config(conn, 1)
        assert float(demo.marge_standard_pct) == 18.0
        assert float(demo.cout_operateur_eur_h) == 70.0
