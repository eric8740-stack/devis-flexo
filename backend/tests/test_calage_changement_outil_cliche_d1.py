"""Lot D1 (e2e) — calage lié au montage, piloté par `changement_outil_cliche`.

POST /api/devis multi-lots :
  - 2 lots même montage, flags False → 1 SEUL calage (lot 2 dédupliqué).
  - 2 lots même montage, lot 2 `changement_outil_cliche=True` → 2 calages
    (vrai 2e jeu d'outil/clichés → calage conservé).
  - mono-lot : toujours 1 calage (flag sans effet).
  - le flag survit au reload du devis.

NON-SACRÉ (value-agnostic) : vérifie la PROPRIÉTÉ de comptage, pas un montant.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique, Devis, Machine, Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)
DEMO = 1
_POSTE_CALAGE = 4


def _fks():
    _onboard_if_needed()
    with SessionLocal() as db:
        m = db.query(Machine).filter_by(entreprise_id=DEMO, actif=True).first()
        c = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=DEMO, actif=True)
            .order_by(CylindreMagnetique.id)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=DEMO, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        return m.id, c.id, mat.id


def _purge():
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.entreprise_id == DEMO).delete()
        db.commit()


def _poste(details: dict, numero: int) -> Decimal:
    p = next(x for x in details["postes"] if x["poste_numero"] == numero)
    return Decimal(str(p["montant_eur"]))


def _marker(details: dict) -> Decimal:
    return Decimal(str(details["calage_montage_deduplique_eur"]))


def _lot(cyl_id, mach_id, mat_id, changement=False):
    return {
        "cylindre_id": cyl_id,
        "machine_id": mach_id,
        "nb_poses_dev": 2,
        "nb_poses_laize": 3,
        "sens_enroulement": 1,
        "quantite": 10_000,
        "matiere_id": mat_id,
        "changement_outil_cliche": changement,
    }


def _post(lots) -> dict:
    mach_id = lots[0]["machine_id"]
    payload = {
        "payload_input": {
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
            "machine_id": mach_id,
        },
        "payload_output": {"mode": "manuel", "prix_vente_ht_eur": "0.00"},
        "statut": "brouillon",
        "quantite_totale": sum(l["quantite"] for l in lots),
        "lots": lots,
    }
    _purge()
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _calage_compte(dpl) -> Decimal:
    """Σ des calages effectivement comptés (poste 4 − marqueur dédup)."""
    total = Decimal("0")
    for lot in dpl:
        d = lot["details"]
        total += _poste(d, _POSTE_CALAGE) - _marker(d)
    return total


def test_deux_lots_sans_changement_un_seul_calage():
    mach, cyl, mat = _fks()
    po = _post([_lot(cyl, mach, mat), _lot(cyl, mach, mat)])
    dpl = po["payload_output"]["details_par_lot"]
    unitaire = _poste(dpl[0]["details"], _POSTE_CALAGE)
    assert unitaire > 0
    assert _marker(dpl[1]["details"]) == unitaire  # lot 2 dédupliqué
    assert _calage_compte(dpl) == unitaire  # 1 calage


def test_deux_lots_avec_changement_outil_deux_calages():
    mach, cyl, mat = _fks()
    po = _post([_lot(cyl, mach, mat), _lot(cyl, mach, mat, changement=True)])
    dpl = po["payload_output"]["details_par_lot"]
    unitaire = _poste(dpl[0]["details"], _POSTE_CALAGE)
    assert unitaire > 0
    assert _marker(dpl[1]["details"]) == 0  # lot 2 : calage CONSERVÉ
    assert _calage_compte(dpl) == unitaire * 2  # 2 calages


def test_mono_lot_un_calage_meme_avec_flag():
    mach, cyl, mat = _fks()
    po = _post([_lot(cyl, mach, mat, changement=True)])
    dpl = po["payload_output"]["details_par_lot"]
    assert _marker(dpl[0]["details"]) == 0
    assert _calage_compte(dpl) == _poste(dpl[0]["details"], _POSTE_CALAGE)


def test_flag_survit_au_reload():
    mach, cyl, mat = _fks()
    po = _post([_lot(cyl, mach, mat), _lot(cyl, mach, mat, changement=True)])
    # via l'id renvoyé, recharge le devis et vérifie le flag persisté.
    with SessionLocal() as db:
        devis = (
            db.query(Devis)
            .filter_by(entreprise_id=DEMO)
            .order_by(Devis.id.desc())
            .first()
        )
        lots = sorted(devis.lots_production, key=lambda lp: lp.ordre)
        assert lots[0].changement_outil_cliche is False
        assert lots[1].changement_outil_cliche is True
