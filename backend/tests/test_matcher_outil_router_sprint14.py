"""Tests du router /api/optimisation/matcher-outil — Sprint 14 Lot 2.

Couvre :
  - 200 happy path : machine_id du tenant demo + brief raisonnable → matches non vide
  - 200 nouvel outil : étiquette trop grande → 1 match cylindre_id=None
  - 404 machine cross-tenant (anti-énumération) via fixture `as_user_b`
  - 422 Pydantic : nb_fronts_min > nb_fronts_max
  - 422 Pydantic : champs manquants ou négatifs
  - 403 si user n'a pas le module flexocompare (fixture `as_user_flexocheck_only`)

Le compte demo (entreprise_id=1) est seedé par l'autouse conftest.
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import Machine

client = TestClient(app)


def _machine_demo_id() -> int:
    """Retourne l'id d'une machine du tenant demo (entreprise_id=1).

    Le seed Sprint 2 alimente la table `machine` avec 3 machines pour le
    compte demo (Mark Andy P5, Daco D250, Atelier 2). Sprint 14 matcher-outil
    consomme `Machine.laize_max_mm` côté router (pas Machine).
    """
    db: Session = SessionLocal()
    try:
        machine = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        assert machine is not None, "seed compte demo doit fournir au moins 1 machine"
        return machine.id
    finally:
        db.close()


def _payload_v1a_like(machine_id: int, **overrides) -> dict:
    """Payload brief client V1a-like (60×40 mm, intervalles 3 mm)."""
    base = {
        "machine_id": machine_id,
        "laize_etiquette_mm": "60",
        "dev_etiquette_mm": "40",
        "intervalle_dev_mm": "3",
        "intervalle_laize_mm": "3",
        "nb_fronts_min": 1,
        "nb_fronts_max": 10,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 200 — happy paths
# ---------------------------------------------------------------------------


def test_matcher_outil_happy_path_v1a_retourne_des_matches():
    """Brief raisonnable sur le compte demo → 200 + matches non vide."""
    machine_id = _machine_demo_id()
    r = client.post("/api/optimisation/matcher-outil", json=_payload_v1a_like(machine_id))

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nb_matches"] >= 1
    assert len(body["matches"]) == body["nb_matches"]
    first = body["matches"][0]
    # Contrat strict — pas de champs accessoires (extra=forbid sur MatcherOutilOut)
    assert set(first.keys()) == {
        "cylindre_id",
        "nb_dents",
        "developpe_mm",
        "nb_poses_dev",
        "nb_poses_laize",
        "nb_poses_total",
        "cout_outil_eur",
        "score_efficacite",
    }
    # Tri par score décroissant (cohérence avec le service)
    scores = [m["score_efficacite"] for m in body["matches"]]
    assert scores == sorted(scores, reverse=True), (
        f"matches non triés par score décroissant : {scores}"
    )


def test_matcher_outil_etiquette_trop_grande_retourne_nouvel_outil():
    """Étiquette dev=500 mm trop grande pour le parc → 1 match cylindre_id=None."""
    machine_id = _machine_demo_id()
    payload = _payload_v1a_like(machine_id, dev_etiquette_mm="500")
    r = client.post("/api/optimisation/matcher-outil", json=payload)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nb_matches"] == 1
    assert body["matches"][0]["cylindre_id"] is None
    # Le coût "nouvel outil" doit être 200 € (constant Lot 2 — TODO Lot 4)
    assert Decimal(body["matches"][0]["cout_outil_eur"]) == Decimal("200")


# ---------------------------------------------------------------------------
# 404 — scope tenant (anti-énumération)
# ---------------------------------------------------------------------------


def test_matcher_outil_404_machine_cross_tenant(as_user_b):
    """User B ne doit pas pouvoir matcher contre une machine du tenant A."""
    # machine_id=1 appartient au tenant A (compte demo, seedé)
    payload = _payload_v1a_like(machine_id=1)
    r = client.post("/api/optimisation/matcher-outil", json=payload)

    assert r.status_code == 404, r.text
    # Détail volontairement neutre (anti-enum : ne révèle pas l'existence)
    assert "not found" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 422 — validations Pydantic
# ---------------------------------------------------------------------------


def test_matcher_outil_422_fronts_min_superieur_max():
    """Validateur cross-field : nb_fronts_min > nb_fronts_max → 422."""
    machine_id = _machine_demo_id()
    payload = _payload_v1a_like(machine_id, nb_fronts_min=5, nb_fronts_max=3)
    r = client.post("/api/optimisation/matcher-outil", json=payload)

    assert r.status_code == 422, r.text


def test_matcher_outil_422_dev_etiquette_nul():
    """dev_etiquette_mm doit être > 0 (Pydantic Field gt=0)."""
    machine_id = _machine_demo_id()
    payload = _payload_v1a_like(machine_id, dev_etiquette_mm="0")
    r = client.post("/api/optimisation/matcher-outil", json=payload)

    assert r.status_code == 422, r.text


def test_matcher_outil_422_champ_inconnu():
    """extra='forbid' sur MatcherOutilIn rejette les champs accessoires."""
    machine_id = _machine_demo_id()
    payload = _payload_v1a_like(machine_id)
    payload["champ_inconnu"] = "boom"
    r = client.post("/api/optimisation/matcher-outil", json=payload)

    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# 403 — module FlexoCompare requis
# ---------------------------------------------------------------------------


def test_matcher_outil_403_si_module_flexocompare_absent(as_user_flexocheck_only):
    """User avec seulement FlexoCheck → 403 sur les routes FlexoCompare."""
    # On utilise machine_id=1 (existe côté demo) — mais le middleware
    # require_module("flexocompare") doit bloquer AVANT le scope check.
    payload = _payload_v1a_like(machine_id=1)
    r = client.post("/api/optimisation/matcher-outil", json=payload)

    assert r.status_code == 403, r.text
