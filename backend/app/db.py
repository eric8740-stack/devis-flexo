import os
from collections.abc import Generator

from sqlalchemy import create_engine
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


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
