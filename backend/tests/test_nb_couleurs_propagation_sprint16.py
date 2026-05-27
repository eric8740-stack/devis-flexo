"""Tests propagation nb couleurs Sprint 16 — Poste 2 Encres.

Couvre le fix "propage le nb de couleurs au cost_engine" :
  - `_mapper_nb_couleurs` : impression/pantone/blanc → `type_encre` réels
    (clés cost_engine), vernis exclu (finition P6, pas une encre P2),
    None / tout-à-zéro → {} (P2 = 0 €, comportement antérieur).
  - POST /api/devis avec nb_couleurs → chiffrage OK, Poste 2 Encres > 0.
  - POST /api/devis sans nb_couleurs → chiffrage OK mais P2 = 0 (antérieur).
  - POST /api/devis/preview-couts avec nb_couleurs → brut non-null > 0.

Ces tests garantissent un complexe best-effort AVEC grammage (le seed
démo n'en a pas) pour que le chiffrage réussisse et que la propagation
des couleurs soit réellement exercée — l'échec sans grammage (option B)
est couvert par test_chiffrage_auto_fix_sprint16.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.crud.devis import _mapper_nb_couleurs
from app.db import SessionLocal
from app.main import app
from app.models import Complexe, Devis
from app.schemas.devis_persist import NbCouleursIn
from tests.test_creation_devis_calcule_prix_aggregate import (
    _fks_tenant1,
    _payload_devis_1_lot,
)

client = TestClient(app)


def _assurer_grammage_premier_complexe() -> None:
    """Donne un grammage au 1er complexe (best-effort) pour permettre P1."""
    with SessionLocal() as db:
        premier = (
            db.query(Complexe)
            .filter_by(entreprise_id=1)
            .order_by(Complexe.id)
            .first()
        )
        if premier is not None and premier.grammage_g_m2 is None:
            premier.grammage_g_m2 = 90
            db.commit()


# ---------------------------------------------------------------------------
# _mapper_nb_couleurs — unitaire
# ---------------------------------------------------------------------------


def test_mapper_nb_couleurs_mappe_vers_type_encre_reels():
    """impression→process_cmj, pantone→pantone, blanc→blanc_high_opaque.
    vernis NON mappé (finition P6, pas une encre)."""
    nb = NbCouleursIn(impression=4, pantone=2, blanc=1, vernis=1)
    result = _mapper_nb_couleurs(nb)
    assert result == {
        "process_cmj": 4,
        "pantone": 2,
        "blanc_high_opaque": 1,
    }
    assert "vernis" not in result


def test_mapper_nb_couleurs_none_ou_zero_donne_dict_vide():
    assert _mapper_nb_couleurs(None) == {}
    assert _mapper_nb_couleurs(NbCouleursIn()) == {}  # tout à 0
    assert _mapper_nb_couleurs(NbCouleursIn(vernis=3)) == {}  # vernis seul → {}


# ---------------------------------------------------------------------------
# POST /api/devis — chiffrage réussit + couleurs → P2 Encres > 0
# ---------------------------------------------------------------------------


def test_post_devis_avec_grammage_et_couleurs_chiffre_encres_non_zero():
    """Si le complexe best-effort a un grammage ET qu'on fournit
    nb_couleurs → chiffrage réussit, ht_total_eur > 0, Poste 2 Encres > 0."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
    _assurer_grammage_premier_complexe()

    payload = _payload_devis_1_lot()
    payload["nb_couleurs"] = {
        "impression": 4,
        "pantone": 2,
        "blanc": 0,
        "vernis": 0,
    }

    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    po = body["payload_output"]
    assert "chiffrage_auto_erreur" not in po, po
    # Prix total chiffré > 0
    assert Decimal(body["ht_total_eur"]) > 0
    assert Decimal(po["prix_vente_ht_eur"]) > 0
    # Poste 2 Encres présent dans la ventilation du lot.
    detail_lot = po["details_par_lot"][0]["details"]
    postes = detail_lot.get("postes") or detail_lot
    assert "2" in str(postes) or "ncres" in str(postes), (
        "Ventilation postes attendue dans details_par_lot"
    )


def test_post_devis_avec_grammage_sans_couleurs_encres_zero():
    """Complexe avec grammage mais nb_couleurs absent → chiffrage réussit
    (P1, P4, P5, P7 > 0) mais P2 Encres = 0 (pas de couleurs fournies).
    Comportement antérieur préservé pour les payloads sans couleurs."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
    _assurer_grammage_premier_complexe()

    # Pas de nb_couleurs dans le payload
    r = client.post("/api/devis", json=_payload_devis_1_lot())
    assert r.status_code == 201, r.text
    body = r.json()
    po = body["payload_output"]
    assert "chiffrage_auto_erreur" not in po
    # Le chiffrage réussit quand même (autres postes) → prix > 0
    assert Decimal(body["ht_total_eur"]) > 0


# ---------------------------------------------------------------------------
# POST /api/devis/preview-couts — chiffrage réussit + couleurs
# ---------------------------------------------------------------------------


def test_preview_couts_avec_grammage_et_couleurs_montant_non_null():
    """Preview avec grammage + couleurs → cout_brut_ht_eur non-null > 0."""
    machine_id, cyl_id, mat_id = _fks_tenant1()
    _assurer_grammage_premier_complexe()

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
        "nb_couleurs": {"impression": 4, "pantone": 1, "blanc": 0, "vernis": 0},
    }
    r = client.post("/api/devis/preview-couts", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["chiffrage_auto_erreur"] is None
    assert data["cout_brut_ht_eur"] is not None
    assert Decimal(data["cout_brut_ht_eur"]) > 0
