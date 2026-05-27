"""Tests fix chiffrage auto Sprint 16 — fin du 0 silencieux (option B).

Couvre la décision produit option B : quand le chiffrage automatique
d'un devis multi-lots échoue (cause connue : matière du lot non reliée
à un complexe de coût — les catalogues `matiere` (optim) et `complexe`
(cost_engine) ne sont pas encore pontés), le devis est créé en état
"chiffrage incomplet" :

  - POST /api/devis      → 201, ht_total_eur NULL, payload_output.
    chiffrage_auto_erreur rempli (PAS de 0 € trompeur, PAS de 500).
  - POST /api/devis/preview-couts → 200, cout_brut/net = None +
    chiffrage_auto_erreur (nom de champ unifié avec POST /devis).

Note liaison matière↔complexe : ce lot N'AJOUTE PAS le pont (chantier
séparé). Le helper garde le complexe best-effort ; quand celui-ci n'a
pas de grammage, le chiffrage échoue PROPREMENT (option B) au lieu de
masquer l'échec derrière un 0 €.

Les cas de chiffrage RÉUSSI + propagation nb couleurs sont couverts par
tests/test_nb_couleurs_propagation_sprint16.py.
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis
from tests.test_creation_devis_calcule_prix_aggregate import _payload_devis_1_lot

client = TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/devis — chiffrage échoue (complexe sans grammage) → option B
# ---------------------------------------------------------------------------


def test_post_devis_complexe_sans_grammage_chiffrage_incomplet():
    """Best-effort prend le 1er complexe (grammage None sur le démo) →
    chiffrage échoue → devis créé 201, ht_total_eur NULL, erreur explicite.
    Aucun 0 trompeur, aucun 500."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()

    r = client.post("/api/devis", json=_payload_devis_1_lot())
    assert r.status_code == 201, r.text  # PAS de 500
    body = r.json()
    po = body["payload_output"]
    # Chiffrage indisponible → erreur explicite + détail technique
    assert "chiffrage_auto_erreur" in po
    assert "non reliée à un complexe" in po["chiffrage_auto_erreur"]
    assert "chiffrage_auto_detail" in po
    # ht_total_eur NULL (pas 0 trompeur)
    assert body["ht_total_eur"] is None


# ---------------------------------------------------------------------------
# POST /api/devis/preview-couts — échec → montants None + erreur
# ---------------------------------------------------------------------------


def test_preview_couts_chiffrage_indisponible_montants_none():
    """Preview avec complexe sans grammage → cout_brut_ht_eur None +
    chiffrage_auto_erreur. Pas de 0 trompeur."""
    from tests.test_creation_devis_calcule_prix_aggregate import _fks_tenant1

    machine_id, cyl_id, mat_id = _fks_tenant1()
    payload = {
        "payload_input": {
            "machine_id": machine_id,
            "format_etiquette_largeur_mm": 100,
            "format_etiquette_hauteur_mm": 80,
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
        "reduction_pct": "0",
    }
    r = client.post("/api/devis/preview-couts", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["chiffrage_auto_erreur"] is not None
    assert "non reliée à un complexe" in data["chiffrage_auto_erreur"]
    assert data["cout_brut_ht_eur"] is None
    assert data["cout_net_ht_eur"] is None
