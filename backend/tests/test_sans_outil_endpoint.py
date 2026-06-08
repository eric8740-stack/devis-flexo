"""Lot back A — contrat /calculer en « mode sans outil » (impression + refente).

Couvre :
  - validateur schéma : `mode_sans_outil=True` exige `laize_stock_mm` ;
  - endpoint `/api/optimisation/calculer` sans outil : court-circuit candidats
    (configs non cylinder-based), `intervalle_dev=0`, `geometrie_laize` enrichie
    (laize_stock / laize_utile / dechet_lateral), écho `mode_sans_outil` ;
  - non-régression : mode AVEC outil (flag absent) → `dechet_lateral_mm=None`.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db import SessionLocal
from app.main import app
from app.models import (
    Bareme,
    CylindreMagnetique,
    Machine,
    Matiere,
    OptionFabrication,
)
from app.schemas.optimisation import OptimisationCalculerRequest
from tests.test_optimisation_router import _onboard_tenant_minimal


client = TestClient(app)


@pytest.fixture
def onboarded():
    db = SessionLocal()
    try:
        for ent_id in (1, 2, 3, 4):
            db.query(CylindreMagnetique).filter_by(entreprise_id=ent_id).delete()
            db.query(Machine).filter_by(entreprise_id=ent_id).delete()
            db.query(Matiere).filter_by(entreprise_id=ent_id).delete()
            db.query(OptionFabrication).filter_by(entreprise_id=ent_id).delete()
            db.query(Bareme).filter_by(entreprise_id=ent_id).delete()
        db.commit()
    finally:
        db.close()
    _onboard_tenant_minimal()


def _payload(**extra) -> dict:
    return {
        "format": {
            "hauteur_mm": 30,
            "largeur_mm": 30,
            "rayon_angles_mm": 2.0,
            "forme_courbe": False,
        },
        "intervalle_dev_min_mm": 2.0,
        "nb_couleurs_impression": 1,
        "quantite": 10_000,
        "options_codes": [],
        **extra,
    }


# ---------------------------------------------------------------------------
# Validateur schéma
# ---------------------------------------------------------------------------


def test_validateur_laize_stock_obligatoire_si_sans_outil():
    """mode_sans_outil=True sans laize_stock_mm → ValidationError."""
    with pytest.raises(ValidationError, match="laize_stock_mm"):
        OptimisationCalculerRequest(
            format={"hauteur_mm": 30, "largeur_mm": 30},
            nb_couleurs_impression=1,
            quantite=1000,
            mode_sans_outil=True,
        )


def test_validateur_sans_outil_avec_stock_ok():
    req = OptimisationCalculerRequest(
        format={"hauteur_mm": 30, "largeur_mm": 30},
        nb_couleurs_impression=1,
        quantite=1000,
        mode_sans_outil=True,
        laize_stock_mm=220,
    )
    assert req.mode_sans_outil is True
    assert float(req.laize_stock_mm) == 220.0


def test_flag_defaut_false_value_neutral():
    req = OptimisationCalculerRequest(
        format={"hauteur_mm": 30, "largeur_mm": 30},
        nb_couleurs_impression=1,
        quantite=1000,
    )
    assert req.mode_sans_outil is False
    assert req.laize_stock_mm is None


# ---------------------------------------------------------------------------
# Endpoint /calculer — sans outil
# ---------------------------------------------------------------------------


def test_calculer_sans_outil_contrat(onboarded):
    """Sans outil : configs émises, court-circuit (cylindre_id=0,
    intervalle_dev=0, nb_poses_dev=1), géométrie laize stock + déchet, écho."""
    r = client.post(
        "/api/optimisation/calculer",
        json=_payload(mode_sans_outil=True, laize_stock_mm=220),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configurations"], "au moins une presse viable attendue"
    cfg = body["configurations"][0]

    # Court-circuit candidats cylindre.
    assert cfg["mode_sans_outil"] is True
    assert cfg["cylindre_id"] == 0
    assert cfg["nb_poses_dev"] == 1
    assert cfg["intervalle_dev_reel_mm"] == 0.0

    # Géométrie sans outil exposée + cohérente : déchet = stock − utile.
    g = cfg["geometrie_laize"]
    assert g["laize_stock_mm"] == 220.0
    assert g["laize_papier_mm"] == 220.0  # P1 facture le stock entier
    assert g["dechet_lateral_mm"] is not None
    assert g["laize_utile_mm"] is not None
    assert g["dechet_lateral_mm"] == pytest.approx(
        220.0 - g["laize_utile_mm"], abs=0.01
    )
    assert g["dechet_lateral_mm"] >= 0.0

    # nb_filles : champ EXPLICITE dans geometrie_laize, cohérent avec
    # nb_poses_laize du candidat (dérivé géométrique par défaut).
    assert g["nb_filles"] is not None
    nb_filles = g["nb_filles"]
    assert nb_filles == cfg["nb_poses_laize"]
    assert nb_filles >= 1
    assert g["laize_utile_mm"] == pytest.approx(
        nb_filles * 30 + (nb_filles - 1) * g["intervalle_laize_mm"], abs=0.01
    )

    # Warning métier non bloquant (déchet facturé).
    assert any("sans outil" in w.lower() for w in body["warnings"])


def test_calculer_sans_outil_nb_filles_force(onboarded):
    """Override nb_filles_force=1 (pas de refente / pistes regroupées) :
    geometrie_laize.nb_filles == 1, déchet recalculé sur 1 fille."""
    r = client.post(
        "/api/optimisation/calculer",
        json=_payload(mode_sans_outil=True, laize_stock_mm=220, nb_filles_force=1),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configurations"]
    cfg = body["configurations"][0]
    g = cfg["geometrie_laize"]
    assert g["nb_filles"] == 1
    assert cfg["nb_poses_laize"] == 1
    # 1 fille de 30 mm → utile 30, déchet = 220 − 30 = 190.
    assert g["laize_utile_mm"] == pytest.approx(30.0)
    assert g["dechet_lateral_mm"] == pytest.approx(190.0)


def test_calculer_avec_outil_non_regression(onboarded):
    """Flag absent (mode avec outil) → chemin cylinder-based inchangé,
    `dechet_lateral_mm`/`laize_stock_mm` absents (None) dans geometrie_laize."""
    r = client.post("/api/optimisation/calculer", json=_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["configurations"]
    cfg = body["configurations"][0]
    assert cfg["mode_sans_outil"] is False
    assert cfg["cylindre_id"] != 0  # vrai cylindre du parc
    g = cfg["geometrie_laize"]
    assert g["dechet_lateral_mm"] is None
    assert g["laize_stock_mm"] is None
    assert g["laize_utile_mm"] is None
    assert g["nb_filles"] is None
