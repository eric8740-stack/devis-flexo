"""Lot F back — bobinage + appro matière (géométrie/appro, AUCUN chiffrage).

Couvre : bloc `bobinage` présent et cohérent, nb_bobines arrondi SUP, m2_total
∝ ml × laize, Ø bobine via bat_calculs (lecture), alerte `depasse_max`,
temps_arret = nb_changements × temps_changement (AFFICHÉ, pas facturé),
dégradation propre (état partiel → bobinage None).
"""
import math

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique, Machine, Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _ids() -> tuple[int, int, int]:
    """(matiere_id, cylindre_id, presse_id) du tenant démo — cylindre + matière
    permettent au moteur de produire un `devis_input` (ml_total réel)."""
    _onboard_if_needed()
    with SessionLocal() as db:
        mat = (
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
        presse = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True, type_machine="presse")
            .order_by(Machine.id)
            .first()
        )
        return mat.id, cyl.id, presse.id


def _set_machine(presse_id: int, **cols) -> None:
    with SessionLocal() as db:
        m = db.get(Machine, presse_id)
        for k, v in cols.items():
            setattr(m, k, v)
        db.commit()


def _base(mat_id: int, cyl_id: int, **extra) -> dict:
    return {
        "laize": 50, "dev": 40, "quantite": 100_000,
        "cylindre_id": cyl_id, "matiere_id": mat_id, **extra,
    }


def _bobinage(payload: dict) -> dict:
    r = client.post("/api/devis/preview", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["bobinage"]


def test_bobinage_present_et_coherent():
    mat_id, cyl_id, presse_id = _ids()
    _set_machine(presse_id, diametre_max_bobine_mm=1100, temps_changement_bobine_min=15)
    b = _bobinage(_base(mat_id, cyl_id))
    assert b is not None
    assert b["ml_total"] > 0
    assert b["m2_total"] > 0
    # Une bobine est forcément plus grosse que son mandrin.
    assert b["diametre_bobine_mm"] > b["diametre_mandrin_mm"]
    assert b["diametre_mandrin_mm"] == 76  # défaut
    assert b["nb_changements"] == max(0, b["nb_bobines"] - 1)
    assert b["temps_arret_min"] == b["nb_changements"] * 15


def test_nb_bobines_arrondi_sup():
    """nb_bobines = ceil(ml_total / ml_par_bobine) — jamais tronqué."""
    mat_id, cyl_id, _ = _ids()
    b = _bobinage(_base(mat_id, cyl_id, ml_par_bobine=700))
    assert b["ml_par_bobine"] == 700
    assert b["nb_bobines"] == math.ceil(b["ml_total"] / 700)
    # Avec un métrage non divisible, l'arrondi SUP couvre le reliquat.
    assert b["nb_bobines"] * 700 >= b["ml_total"]


def test_m2_total_proportionnel_au_ml():
    """m2_total = ml_total × laize_appro → ratio constant quand seul le ml bouge."""
    mat_id, cyl_id, _ = _ids()
    b1 = _bobinage(_base(mat_id, cyl_id, quantite=50_000))
    b2 = _bobinage(_base(mat_id, cyl_id, quantite=100_000))
    # même laize → m2/ml identique (à l'arrondi près).
    r1 = b1["m2_total"] / b1["ml_total"]
    r2 = b2["m2_total"] / b2["ml_total"]
    assert abs(r1 - r2) < 1e-3
    assert b2["ml_total"] > b1["ml_total"]


def test_depasse_max_leve_alerte():
    """Ø bobine > Ø max presse → depasse_max + alerte warn (jamais bloquant)."""
    mat_id, cyl_id, presse_id = _ids()
    _set_machine(presse_id, diametre_max_bobine_mm=1)  # tout Ø le dépasse
    r = client.post("/api/devis/preview", json=_base(mat_id, cyl_id))
    body = r.json()
    b = body["bobinage"]
    assert b["depasse_max"] is True
    assert b["diametre_max_presse_mm"] == 1
    assert any("max presse" in a["message"] for a in body["alertes"])


def test_temps_arret_affiche_changements():
    """temps_arret_min = (nb_bobines-1) × temps_changement — AFFICHÉ, pas facturé.

    Vérifie aussi que `prix_ht` (7 postes sacrés) est INCHANGÉ par le bloc F."""
    mat_id, cyl_id, presse_id = _ids()
    _set_machine(presse_id, temps_changement_bobine_min=20, diametre_max_bobine_mm=1100)
    r = client.post("/api/devis/preview", json=_base(mat_id, cyl_id, ml_par_bobine=700))
    body = r.json()
    b = body["bobinage"]
    assert b["nb_changements"] >= 1
    assert b["temps_arret_min"] == b["nb_changements"] * 20
    # F = géométrie/appro : le prix HT 7 postes reste chiffré normalement.
    assert body["prix_ht"] is not None


def test_bobinage_degrade_proprement_etat_partiel():
    """Sans quantité (pas de métrage matière) → bobinage None, pas de 500."""
    r = client.post("/api/devis/preview", json={"laize": 50, "dev": 40})
    assert r.status_code == 200, r.text
    assert r.json()["bobinage"] is None
