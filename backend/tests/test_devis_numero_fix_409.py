"""Fix 409 — tests dedies de la regression hard-delete + multi-tenant.

Couvre :
  - generate_next_numero utilise MAX(seq)+1 (et non count+1)
    apres un hard-delete d'un numero intermediaire.
  - POST /api/devis ne 409 plus apres hard-delete d'un devis precedent.
  - Deux tenants peuvent avoir chacun DEV-{annee}-0001 sans collision
    (UNIQUE composite scope tenant via migration y9n2i3g7d5f0).

Sources :
  - backend/scripts/repro_409_devis_numero.py (script de diag externe)
  - backend/app/services/numero_devis_service.py (MAX+1 scope tenant)
  - backend/alembic/versions/y9n2i3g7d5f0_devis_numero_unique_per_tenant.py
"""
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from app.main import app
from app.models import Devis
from app.services.numero_devis_service import generate_next_numero
from tests.test_lot_production_model import _onboard_if_needed


client = TestClient(app)
DEMO_ENTREPRISE_ID = 1
USER_B_ENTREPRISE_ID = 2


def _purge_devis_tenant(entreprise_id: int) -> None:
    """Vide la table devis pour ce tenant (utilise dans les seeds de test)."""
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.entreprise_id == entreprise_id).delete()
        db.commit()


def _fks_tenant_demo() -> tuple[int, int, int]:
    """Recupere machine/cylindre/matiere actifs pour le tenant demo."""
    _onboard_if_needed()
    from app.models import CylindreMagnetique, Machine, Matiere

    with SessionLocal() as db:
        machine = (
            db.query(Machine)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .first()
        )
        assert machine and cyl and mat, "seed demo incomplet"
        return machine.id, cyl.id, mat.id


def _payload_post_devis_minimal(qte: int = 10000) -> dict:
    """Payload minimal pour POST /api/devis sur le tenant demo."""
    machine_id, cyl_id, mat_id = _fks_tenant_demo()
    return {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
        },
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "0.00",
        },
        "statut": "brouillon",
        "quantite_totale": qte,
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": qte,
                "matiere_id": mat_id,
            },
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# UNIT : generate_next_numero
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_next_numero_uses_max_plus_one_not_count_plus_one():
    """Apres hard-delete d'un devis intermediaire, le numero suivant est
    MAX(seq)+1 (preserve la sequence) et PAS count+1 (qui reboucherait
    le trou et collisionnerait avec un numero existant)."""
    annee = datetime.now().year
    _purge_devis_tenant(DEMO_ENTREPRISE_ID)

    # Insere 3 devis avec des numeros connus.
    with SessionLocal() as db:
        from app.models import Machine

        mach = (
            db.query(Machine)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .first()
        )
        assert mach is not None
        for seq in (1, 2, 3):
            db.add(Devis(
                entreprise_id=DEMO_ENTREPRISE_ID,
                numero=f"DEV-{annee}-{seq:04d}",
                statut="brouillon",
                payload_input={"placeholder": True},
                payload_output={"placeholder": True},
                mode_calcul="cas1",
                format_h_mm=Decimal("50.00"),
                format_l_mm=Decimal("100.00"),
                machine_id=mach.id,
                type_entree_fichier="a_designer",
            ))
        db.commit()

        # Hard-delete le 0002.
        db.execute(
            text("DELETE FROM devis WHERE numero = :n"),
            {"n": f"DEV-{annee}-0002"},
        )
        db.commit()

        # generate_next_numero -> MAX(3)+1 = 4 (et non count(2)+1 = 3).
        next_num = generate_next_numero(db, DEMO_ENTREPRISE_ID)
        assert next_num == f"DEV-{annee}-0004", (
            f"MAX+1 attendu = DEV-{annee}-0004, recu {next_num} "
            "(regression : retour au count+1 qui rebouche les trous)"
        )


def test_generate_next_numero_scoped_per_tenant():
    """Le compteur est scope tenant : tenant A et tenant B ont chacun leur
    propre sequence, independante de l'autre."""
    annee = datetime.now().year
    _purge_devis_tenant(DEMO_ENTREPRISE_ID)
    _purge_devis_tenant(USER_B_ENTREPRISE_ID)

    # Cree le tenant B s'il n'existe pas (idempotent).
    from tests.conftest import _ensure_user_b

    _ensure_user_b()

    with SessionLocal() as db:
        from app.models import Machine

        mach_demo = (
            db.query(Machine)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .first()
        )
        assert mach_demo is not None

        # Pour tenant B, on cree une machine si besoin (ou on reutilise une
        # machine seedee). Pour simplifier on garde mach_demo.id en croyant
        # que c'est OK (FK lache cote machine, le test n'exerce que le
        # compteur numero).
        db.add(Devis(
            entreprise_id=DEMO_ENTREPRISE_ID,
            numero=f"DEV-{annee}-0001",
            statut="brouillon",
            payload_input={"p": 1}, payload_output={"p": 1},
            mode_calcul="cas1",
            format_h_mm=Decimal("50.00"),
            format_l_mm=Decimal("100.00"),
            machine_id=mach_demo.id,
            type_entree_fichier="a_designer",
        ))
        db.commit()

        # Tenant B n'a rien -> son next = 0001 (independant du tenant demo).
        next_b = generate_next_numero(db, USER_B_ENTREPRISE_ID)
        assert next_b == f"DEV-{annee}-0001", (
            f"Tenant B sans devis devrait demarrer a 0001, recu {next_b}"
        )

        # Tenant demo a deja 0001 -> son next = 0002.
        next_demo = generate_next_numero(db, DEMO_ENTREPRISE_ID)
        assert next_demo == f"DEV-{annee}-0002", (
            f"Tenant demo avec 1 devis devrait avancer a 0002, recu {next_demo}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# E2E : POST /api/devis ne 409 plus apres hard-delete
# ─────────────────────────────────────────────────────────────────────────────


def test_post_devis_after_hard_delete_no_409():
    """E2E : la regression historique. On cree 3 devis via l'API, on en
    hard-delete un intermediaire en SQL, puis un 4e POST doit reussir
    (avant le fix : 409 UNIQUE constraint failed)."""
    annee = datetime.now().year
    _purge_devis_tenant(DEMO_ENTREPRISE_ID)

    # 3 POST successifs.
    created_numeros = []
    for _ in range(3):
        r = client.post("/api/devis", json=_payload_post_devis_minimal())
        assert r.status_code == 201, r.text
        created_numeros.append(r.json()["numero"])
    assert created_numeros == [
        f"DEV-{annee}-0001", f"DEV-{annee}-0002", f"DEV-{annee}-0003"
    ]

    # Hard-delete le 0002 directement en SQL (simule la perte historique
    # qui declenchait le bug).
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM devis WHERE numero = :n"),
            {"n": f"DEV-{annee}-0002"},
        )
        db.commit()

    # 4e POST : doit reussir avec DEV-{annee}-0004 (et non 409).
    r = client.post("/api/devis", json=_payload_post_devis_minimal())
    assert r.status_code == 201, (
        f"Regression 409 : POST apres hard-delete a echoue avec "
        f"{r.status_code} -- detail : {r.text}"
    )
    assert r.json()["numero"] == f"DEV-{annee}-0004"


# ─────────────────────────────────────────────────────────────────────────────
# E2E : multi-tenant
# ─────────────────────────────────────────────────────────────────────────────


def test_two_tenants_can_both_have_dev_yyyy_0001(switch_to_user_b):
    """Deux tenants distincts peuvent chacun avoir DEV-{annee}-0001 sans
    collision sur l'UNIQUE -- car la contrainte est scopee tenant via
    `ix_devis_entreprise_id_numero`."""
    annee = datetime.now().year
    _purge_devis_tenant(DEMO_ENTREPRISE_ID)
    _purge_devis_tenant(USER_B_ENTREPRISE_ID)

    # Tenant demo : 1er devis -> DEV-{annee}-0001.
    r1 = client.post("/api/devis", json=_payload_post_devis_minimal())
    assert r1.status_code == 201, r1.text
    assert r1.json()["numero"] == f"DEV-{annee}-0001"

    # Bascule sur le tenant B.
    switch_to_user_b()

    # NB : le tenant B n'a pas le seed demo (machines, cylindres, ...).
    # Le test couvre uniquement la contrainte UNIQUE -- on insere
    # directement via SQLAlchemy pour ne pas dependre du seed B.
    with SessionLocal() as db:
        from app.models import Machine

        # On reutilise la machine demo (FK lache cote SQLite ; en prod
        # Postgres ce test n'a pas vocation a tourner -- il valide juste
        # la levee de la contrainte UNIQUE globale).
        mach = (
            db.query(Machine)
            .filter_by(entreprise_id=DEMO_ENTREPRISE_ID, actif=True)
            .first()
        )
        assert mach is not None

        d = Devis(
            entreprise_id=USER_B_ENTREPRISE_ID,
            numero=f"DEV-{annee}-0001",  # MEME numero que tenant demo
            statut="brouillon",
            payload_input={"p": 1},
            payload_output={"p": 1},
            mode_calcul="cas1",
            format_h_mm=Decimal("50.00"),
            format_l_mm=Decimal("100.00"),
            machine_id=mach.id,
            type_entree_fichier="a_designer",
        )
        db.add(d)
        # Pas de 409 : la contrainte UNIQUE est sur (entreprise_id, numero).
        db.commit()
        # Sanity : les deux devis coexistent.
        rows = db.execute(
            text(
                "SELECT entreprise_id, numero FROM devis "
                "WHERE numero = :n ORDER BY entreprise_id"
            ),
            {"n": f"DEV-{annee}-0001"},
        ).fetchall()
        assert [(r[0], r[1]) for r in rows] == [
            (DEMO_ENTREPRISE_ID, f"DEV-{annee}-0001"),
            (USER_B_ENTREPRISE_ID, f"DEV-{annee}-0001"),
        ]
