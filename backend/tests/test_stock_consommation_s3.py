"""Module Stock S3 back — lien devis↔stock.

Couvre : proposition FIFO (matière + laize + ml_requis = bobinage.ml_total),
couverture/insuffisance (manque_ml), consommer (mouvements sortie devis_id +
décrément), 409 atomique, annulation (entree inverse, idempotente), guard DELETE
bobine 409, isolation tenant.
"""
import itertools

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import CylindreMagnetique, Devis, LotProduction, Machine, Matiere
from tests.test_lot_production_model import _onboard_if_needed

client = TestClient(app)

_seq = itertools.count(1)


def _devis_avec_lot(quantite: int = 50_000) -> tuple[int, int]:
    """Crée un devis sauvegardé + 1 lot (avec outil) pour le tenant démo.

    Renvoie (devis_id, matiere_id). Le lot porte cylindre/machine/matière seedés
    → `_construire_devis_input_pour_lot` peut calculer `ml_total`.
    """
    _onboard_if_needed()
    with SessionLocal() as db:
        cyl = db.query(CylindreMagnetique).filter_by(entreprise_id=1, actif=True).first()
        mach = (
            db.query(Machine)
            .filter_by(entreprise_id=1, actif=True, type_machine="presse")
            .first()
        )
        mat = db.query(Matiere).filter_by(entreprise_id=1, actif=True).first()
        numero = f"DEV-S3-{next(_seq):04d}"
        devis = Devis(
            entreprise_id=1,
            numero=numero,
            payload_input={
                "machine_id": mach.id,
                "format_etiquette_largeur_mm": 50,
                "format_etiquette_hauteur_mm": 40,
            },
            payload_output={"prix_vente_ht_eur": "0"},
            mode_calcul="manuel",
            ht_total_eur=0,
            format_h_mm=40,
            format_l_mm=50,
            machine_id=mach.id,
        )
        db.add(devis)
        db.flush()
        lot = LotProduction(
            devis_id=devis.id,
            entreprise_id=1,
            ordre=1,
            cylindre_id=cyl.id,
            machine_id=mach.id,
            nb_poses_dev=2,
            nb_poses_laize=3,
            sens_enroulement=1,
            quantite=quantite,
            matiere_id=mat.id,
        )
        db.add(lot)
        db.commit()
        return devis.id, mat.id


def _bobine(matiere_id: int, ml_restant: int, laize_mm: float = 1000) -> dict:
    r = client.post(
        "/api/bobines",
        json={
            "matiere_id": matiere_id,
            "laize_mm": laize_mm,
            "ml_initial": ml_restant,
            "rangee": "C",
            "etage": 0,
            "position": next(_seq),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _proposition(devis_id: int) -> dict:
    r = client.get(f"/api/devis/{devis_id}/proposition-consommation")
    assert r.status_code == 200, r.text
    return r.json()


def test_proposition_ml_requis_et_insuffisance():
    """Sans stock : ml_requis > 0, stock insuffisant, manque_ml == ml_requis."""
    devis_id, _ = _devis_avec_lot()
    p = _proposition(devis_id)
    assert p["ml_requis"] > 0
    assert p["lignes"] == []
    assert p["stock_suffisant"] is False
    assert p["manque_ml"] == p["ml_requis"]


def test_proposition_fifo_couvre_et_ordonne():
    """FIFO : bobine la plus ancienne d'abord, allocation jusqu'à couverture."""
    devis_id, mat_id = _devis_avec_lot()
    requis = int(_proposition(devis_id)["ml_requis"])
    # 2 bobines de la bonne matière, créées dans l'ordre (a plus ancienne que b).
    a = _bobine(mat_id, ml_restant=requis)  # couvre déjà tout
    b = _bobine(mat_id, ml_restant=requis)
    p = _proposition(devis_id)
    assert p["stock_suffisant"] is True
    assert p["manque_ml"] == 0
    # FIFO : la 1ère bobine (a, plus ancienne) est servie en premier et suffit.
    assert p["lignes"][0]["bobine_id"] == a["id"]
    assert p["lignes"][0]["ml_propose"] == requis
    assert all(li["bobine_id"] != b["id"] for li in p["lignes"])  # b non nécessaire


def test_consommer_cree_mouvements_et_decremente():
    devis_id, mat_id = _devis_avec_lot()
    bob = _bobine(mat_id, ml_restant=5000)
    r = client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 1200}]},
    )
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["mouvements"][0]["type"] == "sortie"
    assert out["mouvements"][0]["ml_apres"] == 3800
    assert out["bobines"][0]["ml_restant"] == 3800
    # le mouvement porte le devis_id
    hist = client.get(f"/api/bobines/{bob['id']}/mouvements").json()
    assert hist[0]["devis_id"] == devis_id


def test_consommer_409_atomique():
    """Une ligne dépasse ml_restant → 409, AUCUN effet (atomique)."""
    devis_id, mat_id = _devis_avec_lot()
    b1 = _bobine(mat_id, ml_restant=1000)
    b2 = _bobine(mat_id, ml_restant=10)
    r = client.post(
        f"/api/devis/{devis_id}/consommer",
        json={
            "lignes": [
                {"bobine_id": b1["id"], "ml": 500},
                {"bobine_id": b2["id"], "ml": 9999},
            ]
        },
    )
    assert r.status_code == 409, r.text
    # ni b1 ni b2 modifiées
    assert client.get(f"/api/bobines/{b1['id']}").json()["ml_restant"] == 1000
    assert client.get(f"/api/bobines/{b2['id']}").json()["ml_restant"] == 10


def test_annuler_consommation_reentre_et_idempotent():
    devis_id, mat_id = _devis_avec_lot()
    bob = _bobine(mat_id, ml_restant=2000)
    client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 800}]},
    )
    assert client.get(f"/api/bobines/{bob['id']}").json()["ml_restant"] == 1200
    # annulation → ré-entrée
    r = client.post(f"/api/devis/{devis_id}/annuler-consommation")
    assert r.status_code == 201, r.text
    assert client.get(f"/api/bobines/{bob['id']}").json()["ml_restant"] == 2000
    # idempotent : 2e annulation ne ré-entre rien
    r2 = client.post(f"/api/devis/{devis_id}/annuler-consommation")
    assert r2.json()["mouvements"] == []
    assert client.get(f"/api/bobines/{bob['id']}").json()["ml_restant"] == 2000


def test_proposition_reflete_deja_consomme():
    """Après consommation, la proposition expose deja_consomme + consomme_ml +
    mouvements ; après annulation, retour à l'état initial."""
    devis_id, mat_id = _devis_avec_lot()
    bob = _bobine(mat_id, ml_restant=5000)
    # avant : pas encore consommé
    p0 = _proposition(devis_id)
    assert p0["deja_consomme"] is False
    assert p0["consomme_ml"] == 0
    assert p0["mouvements"] == []
    # consomme
    client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 700}]},
    )
    p1 = _proposition(devis_id)
    assert p1["deja_consomme"] is True
    assert p1["consomme_ml"] == 700
    assert any(m["type"] == "sortie" for m in p1["mouvements"])
    # annule → état initial
    client.post(f"/api/devis/{devis_id}/annuler-consommation")
    p2 = _proposition(devis_id)
    assert p2["deja_consomme"] is False
    assert p2["consomme_ml"] == 0


def test_consommer_refuse_si_deja_consomme_409():
    """Garde back contre la double consommation."""
    devis_id, mat_id = _devis_avec_lot()
    bob = _bobine(mat_id, ml_restant=5000)
    r1 = client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 500}]},
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 100}]},
    )
    assert r2.status_code == 409, r2.text
    # après annulation, on peut reconsommer
    client.post(f"/api/devis/{devis_id}/annuler-consommation")
    r3 = client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 100}]},
    )
    assert r3.status_code == 201, r3.text


def test_mouvements_filtre_devis_id():
    devis_id, mat_id = _devis_avec_lot()
    bob = _bobine(mat_id, ml_restant=5000)
    client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 300}]},
    )
    journal = client.get(f"/api/mouvements?devis_id={devis_id}").json()
    assert len(journal) >= 1
    assert all(m["devis_id"] == devis_id for m in journal)


def test_guard_delete_bobine_avec_mouvements_409():
    devis_id, mat_id = _devis_avec_lot()
    bob = _bobine(mat_id, ml_restant=2000)
    client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": bob["id"], "ml": 100}]},
    )
    r = client.delete(f"/api/bobines/{bob['id']}")
    assert r.status_code == 409, r.text


def test_isolation_cross_tenant_404(switch_to_user_b):
    devis_id, _ = _devis_avec_lot()
    switch_to_user_b()
    assert client.get(
        f"/api/devis/{devis_id}/proposition-consommation"
    ).status_code == 404
    assert client.post(
        f"/api/devis/{devis_id}/consommer",
        json={"lignes": [{"bobine_id": 1, "ml": 1}]},
    ).status_code == 404
    assert client.post(
        f"/api/devis/{devis_id}/annuler-consommation"
    ).status_code == 404
