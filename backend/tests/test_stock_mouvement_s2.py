"""Module Stock S2 back — mouvements (journal d'audit + ajustement ml_restant).

Couvre : entree/sortie/inventaire ajustent `ml_restant` (transactionnel),
audit ml_avant→ml_apres, sortie insuffisante → 409 (atomique, aucun effet),
historique bobine + liste tenant, isolation tenant (cross-tenant 404).
"""
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)


def _matiere_id() -> int:
    _onboard_if_needed()
    with SessionLocal() as db:
        m = (
            db.query(Matiere)
            .filter_by(entreprise_id=1, actif=True)
            .order_by(Matiere.id)
            .first()
        )
        return m.id


def _bobine(ml_initial: int = 2000) -> dict:
    """Crée une bobine du tenant A et renvoie son JSON."""
    r = client.post(
        "/api/bobines",
        json={
            "matiere_id": _matiere_id(),
            "laize_mm": 330,
            "ml_initial": ml_initial,
            "rangee": "B",
            "etage": 1,
            "position": 3,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _mouvement(bobine_id: int, **body) -> "object":
    return client.post(f"/api/bobines/{bobine_id}/mouvements", json=body)


def test_entree_augmente_ml_restant():
    b = _bobine(2000)
    r = _mouvement(b["id"], type="entree", ml=500, motif="réception")
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["mouvement"]["type"] == "entree"
    assert out["mouvement"]["ml_avant"] == 2000
    assert out["mouvement"]["ml_apres"] == 2500
    assert out["bobine"]["ml_restant"] == 2500
    # persistance vérifiée via GET bobine
    assert client.get(f"/api/bobines/{b['id']}").json()["ml_restant"] == 2500


def test_sortie_diminue_ml_restant():
    b = _bobine(2000)
    r = _mouvement(b["id"], type="sortie", ml=300)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["mouvement"]["ml_apres"] == 1700
    assert out["bobine"]["ml_restant"] == 1700


def test_sortie_insuffisante_409_atomique():
    """Sortie > stock → 409, AUCUN effet (ml_restant inchangé, pas de mouvement)."""
    b = _bobine(2000)
    avant = client.get("/api/mouvements").json()
    r = _mouvement(b["id"], type="sortie", ml=3000)
    assert r.status_code == 409, r.text
    # ml_restant inchangé
    assert client.get(f"/api/bobines/{b['id']}").json()["ml_restant"] == 2000
    # aucun mouvement créé pour cette bobine
    hist = client.get(f"/api/bobines/{b['id']}/mouvements").json()
    assert hist == []
    # le journal global n'a pas grossi du fait du refus
    assert len(client.get("/api/mouvements").json()) == len(avant)


def test_inventaire_corrige_et_audit():
    b = _bobine(2000)
    r = _mouvement(b["id"], type="inventaire", ml=1234, motif="comptage")
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["mouvement"]["ml_avant"] == 2000
    assert out["mouvement"]["ml_apres"] == 1234  # ml = nouvelle valeur cible
    assert out["bobine"]["ml_restant"] == 1234


def test_historique_bobine_recent_dabord():
    b = _bobine(2000)
    _mouvement(b["id"], type="entree", ml=100)
    _mouvement(b["id"], type="sortie", ml=50)
    hist = client.get(f"/api/bobines/{b['id']}/mouvements").json()
    assert len(hist) == 2
    # plus récent d'abord : la sortie est le dernier mouvement
    assert hist[0]["type"] == "sortie"


def test_liste_tenant_inclut_les_mouvements():
    b = _bobine(2000)
    _mouvement(b["id"], type="entree", ml=10)
    journal = client.get("/api/mouvements").json()
    assert any(m["bobine_id"] == b["id"] for m in journal)


def test_isolation_cross_tenant_404(switch_to_user_b):
    """B ne peut ni créer un mouvement, ni lire l'historique d'une bobine de A."""
    b = _bobine(2000)
    _mouvement(b["id"], type="entree", ml=100)  # par A
    switch_to_user_b()
    assert _mouvement(b["id"], type="entree", ml=10).status_code == 404
    assert client.get(f"/api/bobines/{b['id']}/mouvements").status_code == 404
    # le journal de B ne voit pas les mouvements de A
    assert client.get("/api/mouvements").json() == []
