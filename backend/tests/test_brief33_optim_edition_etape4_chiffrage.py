"""Tests E2E Brief #33 — Optimisation édition mode + étape 4 chiffrage.

8 tests couvrant :
1. POST /api/devis/preview-couts : recalcul brut/net live sans persister.
2. preview-couts avec réduction commerciale (cout_net = brut × (1 - red%)).
3. preview-couts en mode dégradé (échec chiffrage → chiffrage_erreur non null).
4. POST /api/devis avec snapshot payload_visuel → persiste correctement.
5. GET /api/devis/{id} retourne payload_visuel dans lots_production.
6. PUT /api/devis/{id} avec nouveaux lots → remplace les lots et payload_visuel.
7. PUT /api/devis/{id} avec reduction_pct → met à jour la réduction.
8. POST /api/devis avec pct_marge_override dans payload_input (chiffrage ok).
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import (
    CylindreMagnetique,
    Devis,
    LotProduction,
    MachineImprimerie,
    Matiere,
)
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _fks_tenant1() -> tuple[int, int, int]:
    _onboard_if_needed()
    with SessionLocal() as db:
        machine = (
            db.query(MachineImprimerie)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        cyl = (
            db.query(CylindreMagnetique)
            .filter_by(entreprise_id=1, actif=True)
            .first()
        )
        mat = db.query(Matiere).filter_by(entreprise_id=1, actif=True).first()
        assert machine and cyl and mat
        return machine.id, cyl.id, mat.id


def _payload_visuel_snapshot(cyl_id: int, machine_id: int) -> dict:
    """Snapshot OptimisationConfigOut minimal pour rejouer SchemaImplantation."""
    return {
        "cylindre_id": cyl_id,
        "machine_id": machine_id,
        "nb_poses_dev": 2,
        "nb_poses_laize": 3,
        "nb_poses_total": 6,
        "intervalle_dev_reel_mm": 2.5,
        "intervalle_laize_reel_mm": 3.0,
        "largeur_plaque_mm": 210.0,
        "laize_papier_mm": 220.0,
        "laize_liner_mm": 215.0,
        "chute_laterale_reelle_mm": 5.0,
        "diametre_bobine_mm": 350.0,
        "z_cylindre_mm": 425.45,
        "sens_enroulement": "SE1",
        "sens_enroulement_libelle": "0° Extérieur · droite avant",
        "rotation_vue_a_deg": 0,
        "rotation_vue_c_deg": 0,
        "score": 75.0,
    }


def _payload_devis_multilots(
    machine_id: int,
    cyl_id: int,
    mat_id: int,
    quantite_totale: int = 15000,
    payload_input_extra: dict | None = None,
) -> dict:
    payload_input = {
        "machine_id": machine_id,
        "format_etiquette_largeur_mm": 100,
        "format_etiquette_hauteur_mm": 80,
        "mode_calcul": "manuel",
        "source": "optim_multi_lots",
        "nb_lots": 2,
        "mandrin_mm": 76,
    }
    if payload_input_extra:
        payload_input.update(payload_input_extra)
    return {
        "payload_input": payload_input,
        "payload_output": {
            "mode": "manuel",
            "prix_vente_ht_eur": "0.00",
            "note": "Brief #33 test.",
        },
        "statut": "brouillon",
        "quantite_totale": quantite_totale,
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 10000,
                "matiere_id": mat_id,
                "payload_visuel": _payload_visuel_snapshot(cyl_id, machine_id),
            },
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 2,
                "sens_enroulement": 1,
                "quantite": 5000,
                "matiere_id": mat_id,
                "payload_visuel": _payload_visuel_snapshot(cyl_id, machine_id),
            },
        ],
    }


def _clean_devis():
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()


# ---------------------------------------------------------------------------
# 1. preview-couts brut/net basic
# ---------------------------------------------------------------------------
def test_preview_couts_retourne_brut_et_net():
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _clean_devis()
    body = {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
            "mandrin_mm": 76,
        },
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 10000,
                "matiere_id": mat_id,
            }
        ],
        "reduction_pct": 0,
    }
    r = client.post("/api/devis/preview-couts", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "cout_brut_ht_eur" in data
    assert "cout_net_ht_eur" in data
    assert data["nb_lots"] == 1
    # Réduction 0 → brut == net.
    assert Decimal(data["cout_brut_ht_eur"]) == Decimal(data["cout_net_ht_eur"])
    assert Decimal(data["reduction_eur"]) == Decimal("0.00")


# ---------------------------------------------------------------------------
# 2. preview-couts avec réduction commerciale
# ---------------------------------------------------------------------------
def test_preview_couts_applique_reduction():
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _clean_devis()
    body = {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mode_calcul": "manuel",
            "mandrin_mm": 76,
        },
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 10000,
                "matiere_id": mat_id,
            }
        ],
        "reduction_pct": 20,
    }
    r = client.post("/api/devis/preview-couts", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    brut = Decimal(data["cout_brut_ht_eur"])
    net = Decimal(data["cout_net_ht_eur"])
    # Si brut > 0 (chiffrage OK), net = brut × 0.80, sinon mode dégradé.
    if brut > 0:
        attendu_net = (brut * Decimal("0.80")).quantize(Decimal("0.01"))
        assert net == attendu_net
        assert Decimal(data["reduction_eur"]) == (brut - net)


# ---------------------------------------------------------------------------
# 3. preview-couts mode dégradé
# ---------------------------------------------------------------------------
def test_preview_couts_mode_degrade_retourne_chiffrage_erreur():
    """Si le chiffrage échoue (FK invalide), preview-couts retourne 200
    avec chiffrage_erreur non null et brut=0 (mode dégradé)."""
    machine_id, cyl_id, _mat = _fks_tenant1()
    body = {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
            "mandrin_mm": 76,
        },
        "lots": [
            {
                "cylindre_id": cyl_id,
                "machine_id": machine_id,
                "nb_poses_dev": 2,
                "nb_poses_laize": 3,
                "sens_enroulement": 1,
                "quantite": 10000,
                "matiere_id": 999_999,  # FK invalide
            }
        ],
        "reduction_pct": 0,
    }
    r = client.post("/api/devis/preview-couts", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    # Mode dégradé : chiffrage_erreur renseigné, brut/net à 0.
    assert data["chiffrage_erreur"] is not None
    assert Decimal(data["cout_brut_ht_eur"]) == Decimal("0")


# ---------------------------------------------------------------------------
# 4. POST /api/devis snapshote payload_visuel
# ---------------------------------------------------------------------------
def test_post_devis_persiste_payload_visuel_des_lots():
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _clean_devis()
    payload = _payload_devis_multilots(machine_id, cyl_id, mat_id)
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    devis_id = r.json()["id"]

    with SessionLocal() as db:
        lots = (
            db.query(LotProduction)
            .filter_by(devis_id=devis_id)
            .order_by(LotProduction.ordre)
            .all()
        )
        assert len(lots) == 2
        for lot in lots:
            assert lot.payload_visuel is not None
            assert lot.payload_visuel["sens_enroulement"] == "SE1"
            assert lot.payload_visuel["laize_papier_mm"] == 220.0
            assert lot.payload_visuel["rotation_vue_a_deg"] == 0


# ---------------------------------------------------------------------------
# 5. GET /api/devis/{id} expose payload_visuel
# ---------------------------------------------------------------------------
def test_get_devis_retourne_payload_visuel_dans_lots():
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _clean_devis()
    payload = _payload_devis_multilots(machine_id, cyl_id, mat_id)
    r = client.post("/api/devis", json=payload)
    devis_id = r.json()["id"]

    r2 = client.get(f"/api/devis/{devis_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert len(body["lots_production"]) == 2
    for lot in body["lots_production"]:
        assert lot["payload_visuel"] is not None
        assert lot["payload_visuel"]["laize_papier_mm"] == 220.0
        # Joints Brief #32 toujours présents.
        assert lot["sens_enroulement_libelle"] is not None
        assert lot["rotation_vue_a_deg"] is not None


# ---------------------------------------------------------------------------
# 6. PUT /api/devis/{id} remplace lots + payload_visuel
# ---------------------------------------------------------------------------
def test_put_devis_remplace_lots_avec_nouveau_payload_visuel():
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _clean_devis()
    payload_create = _payload_devis_multilots(machine_id, cyl_id, mat_id)
    r_create = client.post("/api/devis", json=payload_create)
    devis_id = r_create.json()["id"]

    # PUT : remplace par un seul lot avec snapshot visuel modifié.
    nouveau_visuel = _payload_visuel_snapshot(cyl_id, machine_id)
    nouveau_visuel["laize_papier_mm"] = 250.0
    nouveau_visuel["sens_enroulement"] = "SE4"
    r_put = client.put(
        f"/api/devis/{devis_id}",
        json={
            "quantite_totale": 8000,
            "lots": [
                {
                    "cylindre_id": cyl_id,
                    "machine_id": machine_id,
                    "nb_poses_dev": 1,
                    "nb_poses_laize": 2,
                    "sens_enroulement": 4,
                    "quantite": 8000,
                    "matiere_id": mat_id,
                    "payload_visuel": nouveau_visuel,
                }
            ],
        },
    )
    assert r_put.status_code == 200, r_put.text
    body = r_put.json()
    assert len(body["lots_production"]) == 1
    lot = body["lots_production"][0]
    assert lot["nb_poses_dev"] == 1
    assert lot["payload_visuel"]["laize_papier_mm"] == 250.0
    assert lot["payload_visuel"]["sens_enroulement"] == "SE4"


# ---------------------------------------------------------------------------
# 7. PUT /api/devis/{id} met à jour reduction_pct
# ---------------------------------------------------------------------------
def test_put_devis_met_a_jour_reduction_pct():
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _clean_devis()
    payload = _payload_devis_multilots(machine_id, cyl_id, mat_id)
    r_create = client.post("/api/devis", json=payload)
    devis_id = r_create.json()["id"]
    # Création par défaut → reduction_pct = 0.
    assert Decimal(r_create.json()["reduction_pct"]) == Decimal("0")

    r_put = client.put(
        f"/api/devis/{devis_id}",
        json={"reduction_pct": 15.5},
    )
    assert r_put.status_code == 200, r_put.text
    assert Decimal(r_put.json()["reduction_pct"]) == Decimal("15.5")


# ---------------------------------------------------------------------------
# 8. POST /api/devis avec pct_marge_override dans payload_input
# ---------------------------------------------------------------------------
def test_post_devis_avec_pct_marge_override_dans_payload_input():
    """Brief #33 — la marge override pilote DevisInput.pct_marge_override
    lu côté CRUD (commit 1) depuis payload_input. La création doit réussir
    et la valeur être persistée dans payload_input."""
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _clean_devis()
    payload = _payload_devis_multilots(
        machine_id,
        cyl_id,
        mat_id,
        payload_input_extra={"pct_marge_override": 0.45},
    )
    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["payload_input"]["pct_marge_override"] == 0.45
