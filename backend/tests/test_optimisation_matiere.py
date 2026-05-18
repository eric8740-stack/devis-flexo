"""Tests sélecteur matière + auto-fill épaisseur/transparence + isolation
tenant + forçage épaisseur (Règle 7).
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


def _onboard_tenant_minimal_avec_matieres():
    """Idem onboarding minimal mais avec 2 matières (1 transparente + 1 opaque)."""
    payload = {
        "cylindres_developpes_mm": [228.6, 304.8, 330.2, 355.6, 406.4, 457.2],
        "machines_codes": ["mark_andy_2200", "omet_xflex_330"],
        "matieres_codes": ["BOPP_TRANSP_50", "PAP_COUCHE_BRILL_80"],
        "options_codes": ["vernis_selectif"],
    }
    r = client.post("/api/onboarding/initialiser-catalogues", json=payload)
    assert r.status_code == 201, r.text


def _matiere_id_par_code(code: str) -> int:
    db: Session = SessionLocal()
    try:
        m = db.query(Matiere).filter_by(code=code, entreprise_id=1).first()
        assert m is not None, f"Matière {code} introuvable"
        return m.id
    finally:
        db.close()


def _payload_base():
    return {
        "format": {"hauteur_mm": 80, "largeur_mm": 100},
        "intervalle_dev_min_mm": 2.0,
        "nb_couleurs_impression": 4,
        "quantite": 10_000,
        "options_codes": [],
    }


# ---------------------------------------------------------------------------
# Endpoint /api/matieres
# ---------------------------------------------------------------------------


def test_list_matieres_renvoie_du_tenant(cleanup_and_onboard):
    _onboard_tenant_minimal_avec_matieres()
    r = client.get("/api/matieres")
    assert r.status_code == 200
    body = r.json()
    codes = {m["code"] for m in body}
    assert "BOPP_TRANSP_50" in codes
    assert "PAP_COUCHE_BRILL_80" in codes


def test_list_matieres_isolation_tenant(cleanup_and_onboard, switch_to_user_b):
    """User A a 2 matières seedées. User B (tenant vide) → liste vide."""
    _onboard_tenant_minimal_avec_matieres()
    switch_to_user_b()
    r = client.get("/api/matieres")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# Matière dans le payload d'optimisation
# ---------------------------------------------------------------------------


def test_matiere_id_appliquee_auto_fill_epaisseur_et_transparence(
    cleanup_and_onboard,
):
    """Si matiere_id renseigné, l'épaisseur et la transparence viennent de la
    matière catalogue (ignorent epaisseur_matiere_um direct du payload)."""
    _onboard_tenant_minimal_avec_matieres()
    mid = _matiere_id_par_code("BOPP_TRANSP_50")
    payload = _payload_base() | {
        "matiere_id": mid,
        # Ces valeurs DOIVENT être ignorées (la matière prime).
        "epaisseur_matiere_um": 999,
        "matiere_est_transparente": False,
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    assert top1["matiere"]["code"] == "BOPP_TRANSP_50"
    assert top1["epaisseur_appliquee_um"] == 50  # catalogue BOPP_TRANSP_50
    assert top1["matiere"]["est_transparent"] is True


def test_matiere_autre_tenant_404(cleanup_and_onboard, switch_to_user_b):
    """User A créé une matière. User B essaie de l'utiliser → 404."""
    _onboard_tenant_minimal_avec_matieres()
    mid = _matiere_id_par_code("BOPP_TRANSP_50")
    switch_to_user_b()
    payload = _payload_base() | {"matiere_id": mid}
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 404


def test_forcage_epaisseur_sans_motif_422(cleanup_and_onboard):
    _onboard_tenant_minimal_avec_matieres()
    mid = _matiere_id_par_code("PAP_COUCHE_BRILL_80")
    payload = _payload_base() | {
        "matiere_id": mid,
        "epaisseur_matiere_force_um": 100,
        # Pas de motif → 422
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 422


def test_forcage_epaisseur_applique_avec_motif(cleanup_and_onboard):
    """Forçage épaisseur 100 µm sur PAP_COUCHE_BRILL_80 (catalogue NULL)
    avec motif valide → 100 dans la réponse + flag de traçabilité."""
    _onboard_tenant_minimal_avec_matieres()
    mid = _matiere_id_par_code("PAP_COUCHE_BRILL_80")
    payload = _payload_base() | {
        "matiere_id": mid,
        "epaisseur_matiere_force_um": 100,
        "motif_forcage_epaisseur": "Stock fournisseur particulier, 100 µm exact",
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    assert top1["forcage_epaisseur"] is True
    assert top1["epaisseur_appliquee_um"] == 100
    assert "fournisseur" in top1["motif_forcage_epaisseur"]


def test_matiere_optionnelle_retro_compat(cleanup_and_onboard):
    """Sans matiere_id (rétro-compat) → on prend epaisseur_matiere_um direct
    et matiere = None dans la réponse."""
    _onboard_tenant_minimal_avec_matieres()
    payload = _payload_base() | {
        "epaisseur_matiere_um": 145,
        "matiere_est_transparente": False,
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    top1 = r.json()["configurations"][0]
    assert top1["matiere"] is None
    assert top1["epaisseur_appliquee_um"] == 145
    assert top1["forcage_epaisseur"] is False
