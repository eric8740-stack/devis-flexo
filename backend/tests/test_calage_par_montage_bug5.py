"""Tripwire bug #5 (NON-SACRÉ) — 1 calage par montage.

POST /api/devis avec 2 lots de MÊME montage (même cylindre + machine + poses,
matières différentes) → le calage (P4) ne doit être compté qu'UNE fois.

Avant le fix : 2 calages (un par lot) → ce test échoue (marqueur dédup absent /
calage compté 2×). Après le fix : 1 calage (le 2e lot est dédupliqué).

NON-SACRÉ : ne fige pas un montant absolu (value-agnostic). Vérifie la
PROPRIÉTÉ « calage compté une seule fois sur le montage partagé ». Les sacrés
V1a (mono-config) et tripwire P0b (1 lot) ne sont jamais touchés.
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


def _poste(details: dict, numero: int) -> Decimal:
    p = next(x for x in details["postes"] if x["poste_numero"] == numero)
    return Decimal(str(p["montant_eur"]))


def _marker(details: dict) -> Decimal:
    return Decimal(str(details["calage_montage_deduplique_eur"]))


def _fks_demo():
    """Renvoie (machine_id, cylindre_id, matiere_id) déterministes du tenant
    démo. La signature de montage = (cylindre, machine, poses) — INDÉPENDANTE
    de la matière — donc une seule matière suffit (deux lots de même montage)."""
    _onboard_if_needed()  # peuple cylindres / machines catalogue du tenant démo
    with SessionLocal() as db:
        machine = (
            db.query(Machine).filter_by(entreprise_id=DEMO, actif=True).first()
        )
        cyl = (
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
        assert machine and cyl and mat, "seed démo incomplet"
        return machine.id, cyl.id, mat.id


def _purge_devis():
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.entreprise_id == DEMO).delete()
        db.commit()


def _post_2_lots_meme_montage(
    mat_id: int, machine_id: int, cyl_id: int,
    laize_a: int = 3, laize_b: int = 3,
):
    """2 lots : MÊME cylindre + presse + nb_poses_dev (= même montage), avec
    `nb_poses_laize` paramétrable par lot. `laize_a == laize_b` → split simple ;
    `laize_a != laize_b` → cas Eric (laize différente sur le même montage)."""
    def lot(nb_poses_laize: int) -> dict:
        return {
            "cylindre_id": cyl_id,
            "machine_id": machine_id,
            "nb_poses_dev": 2,
            "nb_poses_laize": nb_poses_laize,
            "sens_enroulement": 1,
            "quantite": 10_000,
            "matiere_id": mat_id,
        }
    payload = {
        "payload_input": {
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
            "machine_id": machine_id,
        },
        "payload_output": {"mode": "manuel", "prix_vente_ht_eur": "0.00"},
        "statut": "brouillon",
        "quantite_totale": 20_000,
        "lots": [lot(laize_a), lot(laize_b)],
    }
    _purge_devis()
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    po = r.json()["payload_output"]
    assert po.get("mode") == "multi-lots", (
        f"chiffrage multi-lots attendu, got {po.get('mode')!r} / "
        f"err={po.get('chiffrage_auto_erreur')!r}"
    )
    return po


def test_2_lots_meme_montage_un_seul_calage():
    machine_id, cyl_id, mat_id = _fks_demo()
    po = _post_2_lots_meme_montage(mat_id, machine_id, cyl_id)
    dpl = po["details_par_lot"]
    assert len(dpl) == 2

    d0, d1 = dpl[0]["details"], dpl[1]["details"]
    calage_unitaire = _poste(d0, _POSTE_CALAGE)
    assert calage_unitaire > 0, "le scénario doit comporter un calage non nul"

    # Lot 1 (1er du montage) : calage conservé, pas de dédup.
    assert _marker(d0) == 0
    # Lot 2 (même montage) : calage dédupliqué (= la valeur unitaire).
    assert _marker(d1) == calage_unitaire

    # Propriété « 1 calage par montage » : la somme des calages EFFECTIVEMENT
    # comptés (poste 4 - dédup) sur les 2 lots == exactement 1 calage.
    calage_compte = (_poste(d0, _POSTE_CALAGE) - _marker(d0)) + (
        _poste(d1, _POSTE_CALAGE) - _marker(d1)
    )
    assert calage_compte == calage_unitaire


def test_2_lots_meme_cylindre_laize_differente_un_seul_calage():
    """Cas RÉEL Eric (non couvert par #102) : 2 lots MÊME cylindre + presse +
    nb_poses_dev, mais `nb_poses_laize` DIFFÉRENT (laize changée). Le montage
    est le même (clichés montés inchangés) → 1 SEUL calage.

    Avec l'ancienne signature à 4-uplets (incluant nb_poses_laize), les 2 lots
    avaient des signatures distinctes → 2 calages. Ce test échoue AVANT le fix,
    passe APRÈS (nb_poses_laize retiré de la signature)."""
    machine_id, cyl_id, mat_id = _fks_demo()
    po = _post_2_lots_meme_montage(mat_id, machine_id, cyl_id, laize_a=3, laize_b=2)
    dpl = po["details_par_lot"]
    assert len(dpl) == 2

    d0, d1 = dpl[0]["details"], dpl[1]["details"]
    calage_unitaire = _poste(d0, _POSTE_CALAGE)
    assert calage_unitaire > 0
    # Laize différente mais MÊME montage → lot 2 dédupliqué.
    assert _marker(d0) == 0
    assert _marker(d1) == calage_unitaire
    # Propriété « 1 calage par montage » malgré la laize différente.
    calage_compte = (_poste(d0, _POSTE_CALAGE) - _marker(d0)) + (
        _poste(d1, _POSTE_CALAGE) - _marker(d1)
    )
    assert calage_compte == calage_unitaire


def test_2_lots_meme_montage_total_coherent_avec_lots():
    """Le total agrégé == somme des prix_vente par lot (lot 2 déjà dédupliqué)."""
    machine_id, cyl_id, mat_id = _fks_demo()
    po = _post_2_lots_meme_montage(mat_id, machine_id, cyl_id)
    dpl = po["details_par_lot"]
    somme_lots = sum(Decimal(str(l["prix_vente_ht_eur"])) for l in dpl)
    assert Decimal(str(po["prix_vente_ht_eur"])) == somme_lots
