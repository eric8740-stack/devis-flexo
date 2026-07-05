"""Non-régression E1 (audit 05/07/2026) — PUT /api/devis/{id} et couleurs.

Bug corrigé : `update_devis` rechiffrait les lots SANS passer
`nb_couleurs_par_type` (contrairement au POST, fixé au Sprint 16) →
éditer un devis 4+1 couleurs faisait retomber P2 Encres et P3a Clichés
à 0 € et baissait le HT silencieusement.

Couvre :
  - PUT avec lots + nb_couleurs explicite → P2 > 0 et P3 > 0.
  - PUT avec lots SANS nb_couleurs → fallback sur payload_input.nb_couleurs
    persisté → P2/P3 > 0 et HT identique au POST (mêmes lots).
  - `DevisUpdate.nb_couleurs` ne finit plus dans un setattr fantôme.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis
from tests.test_creation_devis_calcule_prix_aggregate import (
    _payload_devis_1_lot,
)
from tests.test_nb_couleurs_propagation_sprint16 import (
    _assurer_grammage_premier_complexe,
)

client = TestClient(app)

NB_COULEURS_4_PLUS_1 = {"impression": 4, "pantone": 1, "blanc": 0, "vernis": 0}


def _montant_poste(payload_output: dict, numero: int) -> Decimal:
    postes = payload_output["details_par_lot"][0]["details"]["postes"]
    return Decimal(
        str(
            next(
                p["montant_eur"] for p in postes if p["poste_numero"] == numero
            )
        )
    )


def _creer_devis_4_plus_1() -> dict:
    """POST un devis multi-lots 4+1 couleurs (chiffrage auto OK).

    `nb_couleurs` est fourni au niveau racine (consommé par le POST) ET
    dans payload_input (état persistant du workflow optim — c'est lui que
    le fallback du PUT relit)."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
    _assurer_grammage_premier_complexe()

    payload = _payload_devis_1_lot()
    payload["nb_couleurs"] = dict(NB_COULEURS_4_PLUS_1)
    payload["payload_input"]["nb_couleurs"] = dict(NB_COULEURS_4_PLUS_1)

    r = client.post("/api/devis", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "chiffrage_auto_erreur" not in body["payload_output"], body
    return body


def _lots_depuis_devis(body: dict) -> list[dict]:
    lot = body["lots_production"][0]
    return [
        {
            "cylindre_id": lot["cylindre_id"],
            "machine_id": lot["machine_id"],
            "nb_poses_dev": lot["nb_poses_dev"],
            "nb_poses_laize": lot["nb_poses_laize"],
            "sens_enroulement": lot["sens_enroulement"],
            "quantite": lot["quantite"],
            "matiere_id": lot["matiere_id"],
        }
    ]


def test_put_avec_nb_couleurs_explicite_p2_et_p3_non_nuls():
    """PUT lots + nb_couleurs 4+1 → Poste 2 Encres > 0 et Poste 3 > 0."""
    body = _creer_devis_4_plus_1()

    r = client.put(
        f"/api/devis/{body['id']}",
        json={
            "quantite_totale": 10000,
            "lots": _lots_depuis_devis(body),
            "nb_couleurs": dict(NB_COULEURS_4_PLUS_1),
        },
    )
    assert r.status_code == 200, r.text
    po = r.json()["payload_output"]
    assert "chiffrage_auto_erreur" not in po, po
    assert _montant_poste(po, 2) > 0, "P2 Encres retombé à 0 € au PUT (bug E1)"
    assert _montant_poste(po, 3) > 0, "P3 Clichés retombé à 0 € au PUT (bug E1)"


def test_put_sans_nb_couleurs_fallback_payload_input():
    """PUT lots SANS nb_couleurs → fallback sur payload_input.nb_couleurs
    persisté : P2/P3 > 0 et HT strictement identique au POST (mêmes lots,
    mêmes couleurs) — l'édition ne fait plus baisser le prix en silence."""
    body = _creer_devis_4_plus_1()
    ht_apres_post = Decimal(str(body["ht_total_eur"]))
    p2_apres_post = _montant_poste(body["payload_output"], 2)
    assert p2_apres_post > 0  # pré-condition : le POST chiffre bien P2

    r = client.put(
        f"/api/devis/{body['id']}",
        json={
            "quantite_totale": 10000,
            "lots": _lots_depuis_devis(body),
            # PAS de nb_couleurs dans le body : cas UI réel (l'écran
            # d'édition ne renvoie pas toujours les compteurs).
        },
    )
    assert r.status_code == 200, r.text
    put_body = r.json()
    po = put_body["payload_output"]
    assert "chiffrage_auto_erreur" not in po, po
    assert _montant_poste(po, 2) == p2_apres_post
    assert _montant_poste(po, 3) > 0
    assert Decimal(str(put_body["ht_total_eur"])) == ht_apres_post


def test_put_devis_legacy_sans_couleurs_persistees_reste_gracieux():
    """Devis SANS nb_couleurs dans payload_input (legacy) : le PUT passe
    toujours (P2 = 0 €, comportement antérieur — pas de 500)."""
    with SessionLocal() as db:
        db.query(Devis).delete()
        db.commit()
    _assurer_grammage_premier_complexe()

    r = client.post("/api/devis", json=_payload_devis_1_lot())
    assert r.status_code == 201, r.text
    body = r.json()

    r = client.put(
        f"/api/devis/{body['id']}",
        json={"quantite_totale": 10000, "lots": _lots_depuis_devis(body)},
    )
    assert r.status_code == 200, r.text
    po = r.json()["payload_output"]
    assert "chiffrage_auto_erreur" not in po, po
    assert _montant_poste(po, 2) == 0
