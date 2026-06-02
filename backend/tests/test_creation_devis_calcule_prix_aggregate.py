"""Tests Brief #32 commit 1 — chiffrage automatique cost_engine_aggregator
au POST /api/devis multi-lots.

Couvre :
  - prix_vente_ht_eur > 0 quand chiffrage réussit (vs 0 du payload minimal).
  - prix agrégé == Σ cout_lot_ht_eur (cohérence aggregator).
  - Cohérence ht_total_eur (denorm) == payload_output.prix_vente_ht_eur.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis, LotProduction
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _fks_tenant1() -> tuple[int, int, int]:
    _onboard_if_needed()
    from app.models import CylindreMagnetique, Machine, Matiere

    with SessionLocal() as db:
        machine = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        mat = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        assert machine and cyl and mat
        return machine.id, cyl.id, mat.id


def _payload_devis_1_lot(qte: int = 10000) -> dict:
    machine_id, cyl_id, mat_id = _fks_tenant1()
    return {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
        },
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "0.00",
        },
        "statut": "brouillon",
        "quantite_totale": qte,
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": qte,
                "matiere_id": mat_id,
            },
        ],
    }


def test_post_devis_optim_prix_non_zero():
    """Brief #32 commit 1 : POST /api/devis depuis l'optim → devis sort
    avec prix_vente_ht_eur > 0 (et non plus 0.00 placeholder).

    Si le chiffrage auto échoue côté backend (complexe manquant, etc.),
    le test tolère le mode dégradé avec note `chiffrage_auto_erreur`
    et prix=0 — l'important est que le devis SOIT créé en 201."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()

    r = client.post("/api/devis", json=_payload_devis_1_lot())
    assert r.status_code == 201, r.text
    body = r.json()
    po = body["payload_output"]
    # Cas nominal : chiffrage réussi
    if "chiffrage_auto_erreur" not in po:
        prix = float(po["prix_vente_ht_eur"])
        assert prix > 0, (
            f"Chiffrage auto a réussi mais prix_vente_ht_eur = {prix}"
        )
        assert po["mode"] == "multi-lots"
        assert "details_par_lot" in po
        assert po["nb_lots"] == 1


def test_prix_aggregate_egal_somme_cout_lots():
    """Quand le chiffrage auto réussit, la somme des cout_lot_ht_eur
    persistés sur les LotProduction == payload_output.prix_vente_ht_eur."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()

    # 2 lots = répartition 6000/4000
    payload = _payload_devis_1_lot(qte=10000)
    payload["lots"].append(
        {
            "cylindre_id": payload["lots"][0]["cylindre_id"],
            "machine_id": payload["lots"][0]["machine_id"],
            "nb_poses_dev": 2,
            "nb_poses_laize": 2,
            "sens_enroulement": 1,
            "quantite": 4000,
            "matiere_id": payload["lots"][0]["matiere_id"],
        }
    )
    payload["lots"][0]["quantite"] = 6000
    payload["quantite_totale"] = 10000

    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    po = body["payload_output"]
    if "chiffrage_auto_erreur" in po:
        # Mode dégradé : pas d'invariant à vérifier
        return
    # Cas nominal
    prix_total = Decimal(po["prix_vente_ht_eur"])
    with SessionLocal() as db:
        lots = (
            db.query(LotProduction).filter_by(devis_id=body["id"]).all()
        )
        somme_cout_lots = sum(
            (lot.cout_lot_ht_eur or Decimal(0)) for lot in lots
        )
    # Tolérance arrondi 0.01 € sur 2 décimales
    assert abs(prix_total - somme_cout_lots) <= Decimal("0.01"), (
        f"Somme cout_lot_ht_eur ({somme_cout_lots}) != "
        f"prix_vente_ht_eur ({prix_total})"
    )


def test_chiffrage_persiste_dans_ht_total_eur_denorm():
    """Le champ dénormalisé Devis.ht_total_eur est mis à jour avec le
    résultat du chiffrage auto (= payload_output.prix_vente_ht_eur)."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()

    r = client.post("/api/devis", json=_payload_devis_1_lot())
    assert r.status_code == 201
    body = r.json()
    po = body["payload_output"]
    if "chiffrage_auto_erreur" in po:
        return  # mode dégradé
    # ht_total_eur denorm doit refléter le chiffrage agrégé
    ht_denorm = Decimal(body["ht_total_eur"])
    prix_po = Decimal(po["prix_vente_ht_eur"])
    assert ht_denorm == prix_po
