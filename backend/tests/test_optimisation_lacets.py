"""Tests lacets droit/gauche bobine fille.

Convention métier : "lacet" = marge de liner siliconé de chaque côté de
l'étiquette sur la bobine fille livrée au client. Par défaut symétrique
(= intervalle_laize_applique / 2). Asymétrique sur demande.

Borne min 0.5 mm (tolérance refente).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import (
    Bareme,
    CylindreMagnetique,
    Machine,
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
            db.query(Machine).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
        yield
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(Machine).filter_by(entreprise_id=ent_id).delete()
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


def test_lacets_default_symetriques(cleanup_and_onboard):
    """Sans flag asymétrique, lacets = intervalle_laize_applique / 2."""
    _onboard_tenant_minimal()
    r = client.post("/api/optimisation/calculer", json=_payload_base())
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    attendu = top1["intervalle_laize_applique_mm"] / 2
    assert top1["lacet_droit_mm"] == pytest.approx(attendu, abs=0.01)
    assert top1["lacet_gauche_mm"] == pytest.approx(attendu, abs=0.01)
    assert top1["lacets_asymetriques"] is False


def test_lacets_asymetriques_appliques(cleanup_and_onboard):
    """Asymétrique : 1.5 droit + 3.5 gauche."""
    _onboard_tenant_minimal()
    payload = _payload_base() | {
        "lacets_asymetriques": True,
        "lacet_droit_mm": 1.5,
        "lacet_gauche_mm": 3.5,
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    assert top1["lacet_droit_mm"] == 1.5
    assert top1["lacet_gauche_mm"] == 3.5
    assert top1["lacets_asymetriques"] is True


def test_lacets_asymetriques_sans_valeurs_422(cleanup_and_onboard):
    """Flag asymétrique ON sans valeurs → erreur de validation."""
    payload = _payload_base() | {"lacets_asymetriques": True}
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 422


def test_lacet_inferieur_05mm_422(cleanup_and_onboard):
    """Lacet < 0.5 mm rejeté (tolérance refente)."""
    payload = _payload_base() | {
        "lacets_asymetriques": True,
        "lacet_droit_mm": 0.2,
        "lacet_gauche_mm": 2.8,
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 422


def test_laize_liner_inchangee_par_lacets(cleanup_and_onboard):
    """La laize_liner reste pilotée par marge_liner_mm tenant + laize étiq.
    Les lacets n'écrasent PAS cette valeur (ils sont une vue "côté client")."""
    _onboard_tenant_minimal()
    r = client.post("/api/optimisation/calculer", json=_payload_base())
    assert r.status_code == 200
    top1 = r.json()["configurations"][0]
    # laize_liner = laize_etiq (100) + 2 × marge_liner (2.5 default) = 105
    assert top1["laize_liner_mm"] == 105.0
