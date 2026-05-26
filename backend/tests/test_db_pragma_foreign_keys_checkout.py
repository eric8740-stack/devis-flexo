"""Test reproduisant le leak PRAGMA foreign_keys du pool SQLAlchemy.

Scénario :
  1. Checkout d'une connexion depuis le pool → FK doivent être ON.
  2. Code applicatif fait `PRAGMA foreign_keys=OFF` (ex: Alembic
     `batch_alter_table` côté SQLite).
  3. La connexion retourne au pool (close session).
  4. Re-checkout d'une connexion (potentiellement la même row de pool).
  5. **La nouvelle connexion DOIT avoir FK=ON** — garantie défensive
     du listener event `"checkout"` ajouté Sprint 16.

Sans ce listener, le PRAGMA OFF persistait dans la connexion poolée
réutilisée → cascade FK cassée pour les tests suivants → 18 régressions
observées au Lot A initial Sprint 16 (cf. commit history).

Le test est SQLite-only : sur PostgreSQL natif, les FK sont toujours
appliquées globalement (pas de PRAGMA équivalent à toggle).
"""
import pytest
from sqlalchemy import text

from app.db import DATABASE_URL, SessionLocal, engine


pytestmark = pytest.mark.skipif(
    not DATABASE_URL.startswith("sqlite"),
    reason="Le leak PRAGMA est SQLite-only (FK toujours appliquées sur Postgres).",
)


def _pragma_foreign_keys(session) -> int:
    """Lit l'état courant de PRAGMA foreign_keys (0 = OFF, 1 = ON)."""
    return session.execute(text("PRAGMA foreign_keys")).scalar()


def test_pragma_fk_on_au_checkout_initial():
    """Sanity baseline : un checkout fresh a FK=ON (listener `connect`
    + listener `checkout` couvrent ce cas)."""
    with SessionLocal() as session:
        assert _pragma_foreign_keys(session) == 1


def test_pragma_fk_force_on_apres_leak_off_dans_pool():
    """**Le test central** — reproduit exactement le scénario qui a
    causé les 18 régressions du Lot A initial Sprint 16 :

      1. Checkout (FK=ON)
      2. PRAGMA foreign_keys=OFF (simule batch_alter_table)
      3. Retour au pool (session.close)
      4. Re-checkout → DOIT être ON, pas OFF.
    """
    # Étape 1+2 : checkout + leak FK=OFF
    with SessionLocal() as session:
        assert _pragma_foreign_keys(session) == 1
        session.execute(text("PRAGMA foreign_keys=OFF"))
        # On confirme bien que le toggle a pris effet localement
        assert _pragma_foreign_keys(session) == 0
        # Étape 3 : commit ou close → la connexion retourne au pool
        # (avec FK=OFF si pas de listener checkout)
        session.commit()
    # session.__exit__ a fait close() → connexion remise dans le pool

    # Étape 4 : re-checkout. Le listener checkout du Sprint 16 doit
    # forcer PRAGMA foreign_keys=ON à nouveau, peu importe l'état
    # antérieur de la connexion poolée.
    with SessionLocal() as session2:
        assert _pragma_foreign_keys(session2) == 1, (
            "Leak PRAGMA détecté : la connexion poolée a été reprise "
            "avec FK=OFF — le listener `checkout` n'a pas joué."
        )


def test_pragma_fk_force_on_meme_apres_n_checkouts_successifs():
    """Robustesse : 5 cycles successifs leak → close → re-checkout.
    Le listener doit re-forcer FK=ON à CHAQUE checkout."""
    for cycle in range(5):
        with SessionLocal() as session:
            assert _pragma_foreign_keys(session) == 1, (
                f"Cycle {cycle} : connexion checkout avec FK=OFF — "
                f"le listener `checkout` n'est pas appliqué."
            )
            # Leak intentionnel avant retour au pool
            session.execute(text("PRAGMA foreign_keys=OFF"))
            session.commit()
