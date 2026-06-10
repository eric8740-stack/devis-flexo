"""Lot E back — matière → épaisseur → Ø (bat_calculs SSOT, lecture pure).

Couvre : l'épaisseur de la matière choisie pilote le Ø ; fallback 150 µm TRACÉ
(jamais silencieux) ; matiere_id=None value-neutral ; endpoint PATCH épaisseur
(scopé tenant).
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique, Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _matiere_id() -> int:
    return _ids()[0]


def _ids() -> tuple[int, int]:
    """(matiere_id, cylindre_id) du tenant démo — le cylindre permet au Ø d'être
    calculé (devis_input chiffré)."""
    _onboard_if_needed()
    with SessionLocal() as db:
        m = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        return m.id, cyl.id


def _set_epaisseur(matiere_id: int, valeur: int | None) -> None:
    with SessionLocal() as db:
        m = db.get(Matiere, matiere_id)
        m.epaisseur_microns = valeur
        db.commit()


def _base(mat_id: int, cyl_id: int | None = None) -> dict:
    d = {"laize": 100, "dev": 80, "quantite": 10_000, "matiere_id": mat_id}
    if cyl_id is not None:
        d["cylindre_id"] = cyl_id
    return d


def test_epaisseur_matiere_pilote_le_diametre():
    mat_id, cyl_id = _ids()
    _set_epaisseur(mat_id, 60)
    g60 = client.post("/api/devis/preview", json=_base(mat_id, cyl_id)).json()["geometrie"]
    _set_epaisseur(mat_id, 200)
    g200 = client.post("/api/devis/preview", json=_base(mat_id, cyl_id)).json()["geometrie"]
    # L'épaisseur lue vient de la matière ; un film plus épais → Ø plus grand.
    assert g60["epaisseur_utilisee_microns"] == 60
    assert g60["epaisseur_fallback"] is False
    assert g200["epaisseur_utilisee_microns"] == 200
    assert g200["diametre_mm"] > g60["diametre_mm"]


def test_epaisseur_null_fallback_150_trace():
    """Matière sans épaisseur → fallback 150 µm + flag + alerte (jamais
    silencieux)."""
    mat_id = _matiere_id()
    _set_epaisseur(mat_id, None)
    body = client.post("/api/devis/preview", json=_base(mat_id)).json()
    g = body["geometrie"]
    assert g["epaisseur_utilisee_microns"] == 150
    assert g["epaisseur_fallback"] is True
    assert any("150" in a["message"] for a in body["alertes"])


def test_matiere_id_none_value_neutral():
    """matiere_id absent : `epaisseur_um` explicite respecté, pas de fallback."""
    body = client.post("/api/devis/preview", json={
        "laize": 100, "dev": 80, "quantite": 10_000, "epaisseur_um": 90,
    }).json()
    g = body["geometrie"]
    assert g["epaisseur_utilisee_microns"] == 90
    assert g["epaisseur_fallback"] is False


def test_matiere_prioritaire_sur_epaisseur_explicite():
    """matiere_id fourni → c'est l'épaisseur de la matière qui pilote (pas le
    `epaisseur_um` explicite)."""
    mat_id = _matiere_id()
    _set_epaisseur(mat_id, 75)
    g = client.post("/api/devis/preview", json={
        **_base(mat_id), "epaisseur_um": 300,
    }).json()["geometrie"]
    assert g["epaisseur_utilisee_microns"] == 75  # matière, pas 300


def test_patch_matiere_epaisseur_scope_et_effet():
    """PATCH épaisseur (scopé tenant) → la matière est mise à jour ; le preview
    suivant l'utilise sans fallback."""
    mat_id = _matiere_id()
    _set_epaisseur(mat_id, None)
    r = client.patch(f"/api/matieres/{mat_id}", json={"epaisseur_microns": 110})
    assert r.status_code == 200, r.text
    assert r.json()["epaisseur_microns"] == 110
    g = client.post("/api/devis/preview", json=_base(mat_id)).json()["geometrie"]
    assert g["epaisseur_utilisee_microns"] == 110
    assert g["epaisseur_fallback"] is False


def test_patch_matiere_hors_perimetre_404():
    """Matière inexistante / cross-tenant → 404 (anti-énumération)."""
    r = client.patch("/api/matieres/999999", json={"epaisseur_microns": 80})
    assert r.status_code == 404
