import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _resolve_database_url() -> str:
    """DATABASE_URL depuis l'env (prod Railway) ou SQLite local (dev)."""
    url = os.getenv("DATABASE_URL", "sqlite:///./devis_flexo.db")
    # Railway/Heroku livrent parfois `postgres://` (legacy) ; SQLAlchemy 2.x
    # exige `postgresql://`.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


DATABASE_URL = _resolve_database_url()

# SQLite a besoin de `check_same_thread=False` pour fonctionner avec FastAPI
# (qui peut traiter plusieurs requêtes dans des threads différents).
# PostgreSQL n'a pas ce souci.
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Sprint 12 multi-tenant : SQLite désactive les FK par défaut, ce qui empêche
# les CASCADE delete de fonctionner (entreprise → user, etc.). En CI/dev local
# on veut le même comportement que PostgreSQL prod. PRAGMA foreign_keys=ON
# active les FK pour CHAQUE connection SQLite.
# Postgres natif gère les FK CASCADE → no-op pour ce dialect.
#
# Sprint 16 — fix leak PRAGMA : on double les listeners "connect" + "checkout".
# Le "connect" couvre la création physique de la connexion. Le "checkout" est
# déclenché à chaque réutilisation depuis le pool : il garantit que toute
# connexion remise en service force FK=ON, même si un code externe a fait
# PRAGMA foreign_keys=OFF avant le retour au pool (cas typique : Alembic
# batch_alter_table qui toggle FK pour SQLite). Sans ce listener "checkout",
# les 18 régressions observées au Lot A initial Sprint 16 réapparaissent
# (cycle migration intra-test → connexion poolée gardée en FK=OFF → cascade
# DB cassée pour les tests suivants).
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    @event.listens_for(engine, "checkout")
    def _ensure_sqlite_foreign_keys_on_checkout(  # noqa: ARG001
        dbapi_connection, connection_record, connection_proxy
    ):
        """Re-force PRAGMA foreign_keys=ON à chaque checkout du pool.

        Idempotent : si déjà ON, l'opération est un no-op côté SQLite.
        Le coût (1 PRAGMA par checkout) est négligeable vs le risque
        de corruption silencieuse en cas de leak FK=OFF dans le pool.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Rollback en cas d'exception non rattrapée par le code applicatif
        # (ex: IntegrityError sur une contrainte UNIQUE) pour ne pas laisser
        # la session dans un état corrompu.
        db.rollback()
        raise
    finally:
        db.close()
