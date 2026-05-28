"""Tests souveraineté commerciale Règle 7 — forçage intervalle laize.

Vérifie que :
- le motif est obligatoire (≥ 10 caractères) si forçage demandé
- la valeur forcée est bien renvoyée dans `intervalle_laize_applique_mm`
- le moteur "recommandé" reste exposé dans `intervalle_laize_recommande_mm`
  pour traçabilité du delta.

+ même pattern pour `intervalle_dev_force_mm` (audit Règle 7 cohérent).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import (
    Bareme,
    CylindreMagnetique,
    MachineImprimerie,
    Matiere,
    OptionFabrication,
)


client = TestClient(app)


@pytest.fixture
def cleanup_and_onboard():
    db: Session = SessionLocal()
    try:
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
        yield
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(MachineImprimerie).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
    finally:
        db.close()


def _onboard_tenant_minimal():
    payload = {
        "cylindres_developpes_mm": [254.0, 304.8, 330.2, 355.6, 406.4, 457.2],
        "machines_codes": ["mark_andy_2200", "omet_xflex_330"],
        "matieres_codes": [],
        "options_codes": ["vernis_selectif", "dorure_chaud"],
    }
    r = client.post("/api/onboarding/initialiser-catalogues", json=payload)
    assert r.status_code == 201, r.text


def _payload_base():
    return {
        "format": {"hauteur_mm": 80, "largeur_mm": 100},
        "intervalle_dev_min_mm": 2.0,
        "nb_couleurs_impression": 4,
        "quantite": 10_000,
        "options_codes": [],
    }


# ---------------------------------------------------------------------------
# Intervalle laize
# ---------------------------------------------------------------------------


def test_force_intervalle_laize_sans_motif_calcule_avec_warning(cleanup_and_onboard):
    """Souveraineté : forçage laize sans motif n'est PLUS bloquant (200 OK).
    Le motif manquant remonte dans `warnings[]` pour bandeau UI non bloquant."""
    _onboard_tenant_minimal()
    payload = _payload_base() | {"intervalle_laize_force_mm": 7.0}
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    warnings = body.get("warnings") or []
    assert any("forcé à 7" in w.lower() for w in warnings), warnings
    assert any("motif" in w.lower() for w in warnings), warnings


def test_force_intervalle_laize_motif_trop_court_warning_non_bloquant(cleanup_and_onboard):
    """Motif < 10 caractères : calcul exécuté, warning explicite remonté."""
    _onboard_tenant_minimal()
    payload = _payload_base() | {
        "intervalle_laize_force_mm": 7.0,
        "motif_forcage_intervalle_laize": "Trop",
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    warnings = r.json().get("warnings") or []
    assert any("motif" in w.lower() and "court" in w.lower() for w in warnings), warnings


def test_force_intervalle_laize_negatif_ou_zero_reste_422(cleanup_and_onboard):
    """Garde-fou : valeur techniquement impossible (≤ 0) reste rejetée 422
    par Pydantic (Field gt=0). On garde le blocage pour ces cas absurdes."""
    _onboard_tenant_minimal()
    payload_zero = _payload_base() | {
        "intervalle_laize_force_mm": 0.0,
        "motif_forcage_intervalle_laize": "Motif suffisamment long ici",
    }
    r0 = client.post("/api/optimisation/calculer", json=payload_zero)
    assert r0.status_code == 422

    payload_neg = _payload_base() | {
        "intervalle_laize_force_mm": -1.0,
        "motif_forcage_intervalle_laize": "Motif suffisamment long ici",
    }
    rn = client.post("/api/optimisation/calculer", json=payload_neg)
    assert rn.status_code == 422


def test_force_intervalle_laize_applique_correctement(cleanup_and_onboard):
    """Forçage à 7 mm avec motif valide : le moteur consomme désormais la
    valeur (bypass du plafond 5 mm) — `intervalle_laize_reel_mm` (Δ laize
    affiché côté UI) reflète la valeur forcée, pas le ratio géométrique."""
    _onboard_tenant_minimal()
    payload = _payload_base() | {
        "intervalle_laize_force_mm": 7.0,
        "motif_forcage_intervalle_laize": "Client demande lacet large pour rebobinage spécifique",
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    assert top1["forcage_intervalle_laize"] is True
    assert top1["intervalle_laize_applique_mm"] == 7.0
    # Δ laize côté UI = intervalle_laize_reel_mm (sortie moteur).
    # Doit refléter la valeur forcée (sinon, le bug Eric : « calcule 5 mm
    # alors que j'ai demandé 7 mm » réapparaît).
    assert top1["intervalle_laize_reel_mm"] == 7.0
    # Le moteur ayant consommé la valeur, recommande == applique : on ne
    # peut plus distinguer « ce que le moteur aurait fait sans forçage »
    # sans double-pass — c'est un compromis assumé du fix.
    assert top1["intervalle_laize_recommande_mm"] == 7.0
    assert "rebobinage" in top1["motif_forcage_intervalle_laize"]


def test_sans_forcage_intervalle_laize_recommande_egal_applique(cleanup_and_onboard):
    _onboard_tenant_minimal()
    r = client.post("/api/optimisation/calculer", json=_payload_base())
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    assert top1["forcage_intervalle_laize"] is False
    assert top1["motif_forcage_intervalle_laize"] is None
    assert top1["intervalle_laize_recommande_mm"] == top1["intervalle_laize_applique_mm"]


# ---------------------------------------------------------------------------
# Intervalle dev (même pattern — Règle 7 cohérence)
# ---------------------------------------------------------------------------


def test_force_intervalle_dev_sans_motif_422(cleanup_and_onboard):
    _onboard_tenant_minimal()
    payload = _payload_base() | {"intervalle_dev_force_mm": 4.0}
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 422


def test_force_intervalle_dev_applique(cleanup_and_onboard):
    _onboard_tenant_minimal()
    payload = _payload_base() | {
        "intervalle_dev_force_mm": 4.0,
        "motif_forcage_intervalle_dev": "Cas particulier client testé en interne",
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    assert top1["forcage_intervalle_dev"] is True
    assert top1["intervalle_dev_applique_mm"] == 4.0
    # Le moteur a recalculé son intervalle_dev_reel basé sur 4 mm → ≥ 4 mm
    assert top1["intervalle_dev_reel_mm"] >= 4.0
