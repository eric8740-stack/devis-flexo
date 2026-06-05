"""L1 géométrie laize — bord latéral surchargeable + laize_papier déterministe.

Couvre :
  - `calcul_laize_papier` : plancher `laize_mini_roulable_mm` (défaut 0 →
    non-régressif ; relevé → laize papier ne descend pas sous le plancher).
  - POST /api/optimisation/calculer : contrat `geometrie_laize` exposé ;
    bord NULL → laize papier == valeur actuelle (chute_min) ; bord surchargé →
    laize papier = plaque + 2×bord (arrondi palier) + écho souveraineté
    (forcage_bord_lateral + warning si motif absent).

SACRED : P1 INTOUCHÉ (cost_engine). Ces champs sont géométrie/affichage.
"""
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import (
    Bareme,
    CylindreMagnetique,
    Machine,
    Matiere,
    OptionFabrication,
)
from app.services.optimisation.bat_calculs import calcul_laize_papier
from tests.test_optimisation_router import _onboard_tenant_minimal


client = TestClient(app)

# Params entreprise démo (seed) : chute latérale mini + palier.
_CHUTE_MIN = 10.0
_PALIER = 10


def _laize_utile_machine(machine_id: int) -> float:
    """Laize utile (mm) de la machine candidate — plafond L2 du papier."""
    with SessionLocal() as db:
        m = db.get(Machine, machine_id)
        assert m is not None and m.laize_utile_mm is not None
        return float(m.laize_utile_mm)


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


def _calculer(**extra) -> dict:
    payload = {
        "format": {
            "hauteur_mm": 30,
            "largeur_mm": 30,
            "rayon_angles_mm": 2.0,
            "forme_courbe": False,
        },
        "intervalle_dev_min_mm": 2.0,
        "nb_couleurs_impression": 4,
        "quantite": 10_000,
        "options_codes": [],
        **extra,
    }
    r = client.post("/api/optimisation/calculer", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Unitaire — plancher laize_mini_roulable (bat_calculs)
# ---------------------------------------------------------------------------


def test_plancher_defaut_zero_non_regressif():
    """Plancher 0 (défaut) → laize papier inchangée (plaque + 2×chute, palier)."""
    assert calcul_laize_papier(205.0, 10.0, 10) == 230
    assert calcul_laize_papier(205.0, 10.0, 10, 0.0) == 230


def test_plancher_releve_force_la_laize_mini():
    """Plancher > laize calculée → la laize papier remonte au plancher."""
    # plaque 205 + 2×10 = 225 → palier 10 → 230 ; plancher 300 → 300.
    assert calcul_laize_papier(205.0, 10.0, 10, 300.0) == 300
    # plancher 100 < 230 → sans effet.
    assert calcul_laize_papier(205.0, 10.0, 10, 100.0) == 230


# ---------------------------------------------------------------------------
# Endpoint /calculer — geometrie_laize + bord
# ---------------------------------------------------------------------------


def test_geometrie_laize_exposee_et_coherente(onboarded):
    body = _calculer()
    cfg = body["configurations"][0]
    g = cfg["geometrie_laize"]
    assert set(g.keys()) == {
        "laize_plaque_mm",
        "bord_lateral_mm",
        "laize_papier_mm",
        "intervalle_laize_mm",
    }
    # Cohérence interne (L2) : laize_papier == min(arrondi_palier(plaque +
    # 2×bord), laize_utile machine candidate).
    lu = _laize_utile_machine(cfg["machine_id"])
    attendu = calcul_laize_papier(
        g["laize_plaque_mm"], g["bord_lateral_mm"], _PALIER, 0.0, lu
    )
    assert g["laize_papier_mm"] == attendu


def test_bord_null_defaut_chute_min_non_regression(onboarded):
    """Sans surcharge : bord effectif == chute_min ; laize papier = plaque +
    2×chute (arrondi palier) PLAFONNÉE à laize_utile. forcage_bord_lateral=False."""
    body = _calculer()
    cfg = body["configurations"][0]
    g = cfg["geometrie_laize"]
    assert g["bord_lateral_mm"] == _CHUTE_MIN
    lu = _laize_utile_machine(cfg["machine_id"])
    assert g["laize_papier_mm"] == calcul_laize_papier(
        g["laize_plaque_mm"], _CHUTE_MIN, _PALIER, 0.0, lu
    )
    assert cfg["forcage_bord_lateral"] is False


def test_bord_surcharge_reflete_laize_papier_et_echo(onboarded):
    """Bord surchargé à 20 mm → laize papier = min(plaque + 2×20 arrondi,
    laize_utile) (L2 : le plafond ROGNE le bord quand il dépasse la presse) ;
    écho forcage + motif ; warning si motif absent."""
    body = _calculer(bord_lateral_mm=20)
    cfg = body["configurations"][0]
    g = cfg["geometrie_laize"]
    assert g["bord_lateral_mm"] == 20.0
    lu = _laize_utile_machine(cfg["machine_id"])
    assert g["laize_papier_mm"] == calcul_laize_papier(
        g["laize_plaque_mm"], 20.0, _PALIER, 0.0, lu
    )
    # Le plafond ne laisse jamais dépasser la laize utile presse.
    assert g["laize_papier_mm"] <= lu
    assert cfg["forcage_bord_lateral"] is True
    # Surcharge sans motif → warning non bloquant (Règle 7).
    assert any("bord latéral" in w.lower() for w in body["warnings"])


def test_bord_surcharge_plus_large_que_defaut(onboarded):
    """Un bord plus large que chute_min donne une laize papier >= au défaut."""
    defaut = _calculer()["configurations"][0]["geometrie_laize"]["laize_papier_mm"]
    surcharge = _calculer(bord_lateral_mm=30)["configurations"][0][
        "geometrie_laize"
    ]["laize_papier_mm"]
    assert surcharge >= defaut


def test_bord_surcharge_avec_motif_pas_de_warning_motif(onboarded):
    body = _calculer(
        bord_lateral_mm=20,
        motif_bord_lateral="surplus client pour refente externe atelier",
    )
    assert not any("motif de surcharge bord" in w.lower() for w in body["warnings"])
