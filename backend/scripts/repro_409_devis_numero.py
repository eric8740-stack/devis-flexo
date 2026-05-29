"""Repro / validation du fix 409 sur POST /api/devis.

Avant le fix : H1 (count+1 non scope tenant) -> UniqueViolation devis.numero.
Apres le fix (migration y9n2i3g7d5f0 + MAX+1 scope tenant) : aucun 409.

Scenario A -- diag, NE TOUCHE PAS la dev DB :
  1. SQLite ephemere + alembic upgrade head (HEAD = y9n2i3g7d5f0 ou plus)
  2. Setup minimal : 1 Entreprise + 1 Machine (FK satisfaites)
  3. Insere 3 devis DEV-{annee}-0001/0002/0003 via SQLAlchemy direct
  4. Hard-delete le 0002 en SQL brut
  5. Appelle generate_next_numero(db, entreprise_id)
     -> AVANT fix : retournait "DEV-{annee}-0003" (count+1 sur 2 lignes)
     -> APRES fix : retourne "DEV-{annee}-0004" (MAX(seq)+1 = 3+1)
  6. Insere un 4e devis avec ce numero -> doit reussir (pas de 409)

Sortie attendue post-fix :
    [VERDICT] PAS DE 409 -- H1 ECARTEE (fix actif)

Sc B (cross-tenant) : verifie qu'apres migration, deux tenants peuvent avoir
chacun DEV-{annee}-0001 sans collision (l'UNIQUE est scopee).
"""
from __future__ import annotations

import os
import sys
import tempfile
import traceback
from decimal import Decimal
from pathlib import Path


def main() -> int:
    # ── 1) DB éphémère ────────────────────────────────────────────────────
    tmpdir = tempfile.mkdtemp(prefix="repro_409_")
    db_path = Path(tmpdir) / "repro.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    print(f"[setup] DB = {db_path}")

    # Alembic upgrade head AVANT tout import models/db en cache.
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(
        str(Path(__file__).resolve().parent.parent / "alembic.ini")
    )
    alembic_cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(alembic_cfg, "head")
    print("[setup] alembic upgrade head OK")

    # Imports après que DATABASE_URL soit posé + tables créées.
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["DATABASE_URL"])
    # SQLite : activer FK pour ne pas masquer une éventuelle FK invalide.
    with engine.connect() as c:
        c.execute(text("PRAGMA foreign_keys = ON"))
        c.commit()
    SessionLocal = sessionmaker(bind=engine)

    from app.models import Devis, Entreprise, Machine
    from app.services.numero_devis_service import generate_next_numero

    # ── 2) Setup minimal : 1 entreprise + 1 machine ───────────────────────
    db = SessionLocal()
    ent = Entreprise(
        raison_sociale="Repro 409 SARL",
        siret="00000000000000",
    )
    db.add(ent)
    db.flush()
    print(f"[setup] entreprise_id = {ent.id}")

    mach = Machine(
        entreprise_id=ent.id,
        nom="Mark Andy Repro",
        laize_max_mm=Decimal("330.00"),
        actif=True,
    )
    db.add(mach)
    db.flush()
    print(f"[setup] machine_id = {mach.id}")

    # Helper local : construit un Devis minimal avec les NOT NULL satisfaits.
    def make_devis(numero: str) -> Devis:
        return Devis(
            entreprise_id=ent.id,
            numero=numero,
            statut="brouillon",
            payload_input={"placeholder": True},
            payload_output={"placeholder": True},
            mode_calcul="cas1",
            format_h_mm=Decimal("50.00"),
            format_l_mm=Decimal("100.00"),
            machine_id=mach.id,
            type_entree_fichier="a_designer",
        )

    # ── 3) Insère DEV-2026-0001/0002/0003 ─────────────────────────────────
    from datetime import datetime

    annee = datetime.now().year
    for seq in (1, 2, 3):
        d = make_devis(f"DEV-{annee}-{seq:04d}")
        db.add(d)
    db.commit()
    print(f"[seed] 3 devis créés : DEV-{annee}-0001 / 0002 / 0003")

    # ── 4) Hard-delete le n°0002 en SQL brut ──────────────────────────────
    n = (
        db.execute(
            text(
                "DELETE FROM devis WHERE numero = :num"
            ),
            {"num": f"DEV-{annee}-0002"},
        ).rowcount
    )
    db.commit()
    print(f"[hard-delete] {n} ligne supprimée (DEV-{annee}-0002)")

    # ── 5) generate_next_numero -> quel numéro propose-t-il ? ──────────────
    next_numero = generate_next_numero(db, ent.id)
    print(f"[generate_next_numero] propose : {next_numero!r}")

    # Sanity : compte ce qui reste
    rows = db.execute(
        text(
            "SELECT numero FROM devis WHERE numero LIKE :pfx ORDER BY numero"
        ),
        {"pfx": f"DEV-{annee}-%"},
    ).fetchall()
    print(f"[state] devis restants : {[r[0] for r in rows]}")
    print(f"[state] count : {len(rows)}  -> next = count+1 = "
          f"DEV-{annee}-{len(rows)+1:04d}")

    # ── 6) POST 4e devis avec ce numéro -> on s'attend à IntegrityError ────
    print(f"\n[ACTE] Tentative INSERT Devis(numero={next_numero!r}) …")
    db_new = SessionLocal()
    try:
        d = Devis(
            entreprise_id=ent.id,
            numero=next_numero,
            statut="brouillon",
            payload_input={"placeholder": True},
            payload_output={"placeholder": True},
            mode_calcul="cas1",
            format_h_mm=Decimal("50.00"),
            format_l_mm=Decimal("100.00"),
            machine_id=mach.id,
            type_entree_fichier="a_designer",
        )
        db_new.add(d)
        db_new.commit()
    except IntegrityError as exc:
        print("\n========== IntegrityError CAPTURÉE ==========")
        print(f"exc class    : {type(exc).__name__}")
        print(f"str(exc)     : {exc}")
        print(f"exc.orig cls : {type(exc.orig).__name__ if exc.orig else None}")
        print(f"exc.orig     : {exc.orig}")
        print(f"exc.statement: {exc.statement}")
        print(f"exc.params   : {exc.params}")
        print("=== TRACEBACK ===")
        traceback.print_exc()
        print("==================")
        db_new.rollback()
        # Confirmation H1 : la contrainte qui saute doit être sur `numero`.
        msg = str(exc).lower()
        if "numero" in msg or "unique" in msg:
            print("\n[VERDICT] H1 CONFIRMÉE — collision UNIQUE sur devis.numero")
            return 0
        print("\n[VERDICT] IntegrityError autre que H1 — voir détails ci-dessus")
        return 2
    else:
        print("\n[VERDICT] PAS DE 409 — H1 INFIRMÉE en local "
              "(le 2e INSERT a réussi sans collision)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
