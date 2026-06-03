"""Tests bug #6 étape 6.2e-back — coût rebobinage PERSISTÉ par lot.

POST /api/devis/{id}/rebobinage-multilots : persiste le coût rebobinage par
lot (épaisseur réelle de la matière du lot + paroi) dans
`payload_output["rebobinage_multilots"]`, agrégé.

SACRÉ : ligne ADDITIVE — `devis.ht_total_eur` (denorm cost_engine) reste
EXACT après apply. Le rebobinage est un coût SÉPARÉ des 7 postes, jamais
fusionné au benchmark. `bat_calculs`/`rotation_se` intouchés.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis, MachineRebobineuse, Matiere, ParametreMandrin


_http = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_machine(db, nom="Rebob apply multilots") -> int:
    mach = MachineRebobineuse(
        entreprise_id=1,
        nom=nom,
        marque="MarqueTest",
        modele="RT100",
        laize_max_mm=Decimal("250"),
        diametre_max_mm=500,
        mandrins_supportes=[25, 38, 76, 152],
        vitesse_pratique_m_min=80,
        cout_horaire_eur=Decimal("45.00"),
        temps_changement_bobine_min=Decimal("1.50"),
        options=[],
        actif=True,
    )
    db.add(mach)
    db.commit()
    db.refresh(mach)
    return mach.id


def _set_paroi_tenant(db, paroi_mm, entreprise_id=1) -> None:
    row = (
        db.query(ParametreMandrin).filter_by(entreprise_id=entreprise_id).first()
    )
    if row is None:
        row = ParametreMandrin(
            entreprise_id=entreprise_id,
            scie_disponible=True,
            mode_par_defaut="auto",
            epaisseur_paroi_mm=paroi_mm,
        )
        db.add(row)
    else:
        row.epaisseur_paroi_mm = paroi_mm
    db.commit()


def _create_matiere(db, code, epaisseur_microns) -> int:
    mat = Matiere(
        entreprise_id=1,
        code=code,
        libelle=f"Mat {code}",
        epaisseur_microns=epaisseur_microns,
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat.id


def _create_devis(db, numero="TEST-RBML-001", ht="1449.09") -> int:
    devis = Devis(
        entreprise_id=1,
        numero=numero,
        payload_input={"machine_id": 1, "format_h_mm": 80, "format_l_mm": 100},
        payload_output={"prix_vente_ht_eur": ht},
        mode_calcul="manuel",
        ht_total_eur=Decimal(ht),  # sacré V1a EXACT
        format_h_mm=80,
        format_l_mm=100,
        machine_id=1,
    )
    db.add(devis)
    db.commit()
    db.refresh(devis)
    return devis.id


def _lot(*, nb=10000, mandrin=76, dmax=300, matiere_id=None,
         epaisseur_saisie_um=None, paroi_override_mm=None, nb_etiq_fixe=None) -> dict:
    return {
        "nb_etiquettes_total": nb,
        "intervalle_developpe_mm": "80",
        "diametre_mandrin_mm": mandrin,
        "diametre_max_bobine_mm": dmax,
        "nb_etiq_par_bobine_fixe": nb_etiq_fixe,
        "matiere_id": matiere_id,
        "epaisseur_saisie_um": epaisseur_saisie_um,
        "paroi_override_mm": paroi_override_mm,
    }


def _payload(machine_id, lots) -> dict:
    return {
        "lots": lots,
        "machine_rebobineuse_id": machine_id,
        "tarifs_mandrins": {
            "prix_pre_coupe_par_mandrin_eur": "5",
            "cout_decoupe_interne_par_mandrin_eur": "2",
            "cout_fixe_decoupe_interne_eur": "39",
        },
        "mode": "auto",
        "motif_force": None,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_apply_persiste_cout_par_lot_et_agregat():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        mat = _create_matiere(db, "APPLY_50", 50)
        did = _create_devis(db, numero="TEST-RBML-AGG")

    r = _http.post(
        f"/api/devis/{did}/rebobinage-multilots",
        json=_payload(mid, [_lot(matiere_id=mat), _lot(matiere_id=mat)]),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nb_lots"] == 2
    assert len(data["lots"]) == 2
    # Agrégat = somme des coûts par lot.
    somme = sum(
        Decimal(l["rebobinage"]["cout_total_rebobinage_eur"]) for l in data["lots"]
    )
    assert Decimal(data["cout_total_rebobinage_eur"]) == somme

    # Persistance dans payload_output["rebobinage_multilots"].
    with SessionLocal() as db:
        devis = db.get(Devis, did)
        ligne = devis.payload_output["rebobinage_multilots"]
        assert ligne["applique"] is True
        assert ligne["nb_lots"] == 2
        assert len(ligne["lots"]) == 2
        assert ligne["lots"][0]["epaisseur_effective_um"] == 50.0
        assert ligne["lots"][0]["epaisseur_source"] == "matiere"


def test_apply_ht_total_inchange_sacred():
    """Ligne ADDITIVE : ht_total_eur (denorm cost_engine) reste EXACT."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        did = _create_devis(db, numero="TEST-RBML-HT", ht="1449.09")

    r = _http.post(
        f"/api/devis/{did}/rebobinage-multilots",
        json=_payload(mid, [_lot(epaisseur_saisie_um="60")]),
    )
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        devis = db.get(Devis, did)
        assert devis.ht_total_eur == Decimal("1449.09")  # INCHANGÉ
        assert devis.payload_output["prix_vente_ht_eur"] == "1449.09"


def test_apply_deux_matieres_differentes_couts_distincts():
    """≥2 lots de matières différentes → coûts par lot reflètent chaque
    épaisseur réelle (pas une seule spec figée 150 µm)."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        fine = _create_matiere(db, "APPLY_FINE", 40)
        epaisse = _create_matiere(db, "APPLY_EPAISSE", 250)
        did = _create_devis(db, numero="TEST-RBML-2MAT")

    r = _http.post(
        f"/api/devis/{did}/rebobinage-multilots",
        json=_payload(mid, [_lot(matiere_id=fine), _lot(matiere_id=epaisse)]),
    )
    assert r.status_code == 200, r.text
    lots = r.json()["lots"]
    assert lots[0]["epaisseur_effective_um"] == 40.0
    assert lots[1]["epaisseur_effective_um"] == 250.0
    # Matière épaisse → moins d'étiq/bobine → plus de bobines que la fine.
    assert (
        lots[1]["rebobinage"]["bobines"]["nb_bobines"]
        >= lots[0]["rebobinage"]["bobines"]["nb_bobines"]
    )


def test_apply_override_paroi_impacte_cout():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        did = _create_devis(db, numero="TEST-RBML-PAROI")

    lots = [
        _lot(epaisseur_saisie_um="60", paroi_override_mm=20),
        _lot(epaisseur_saisie_um="60", paroi_override_mm=0),
    ]
    r = _http.post(
        f"/api/devis/{did}/rebobinage-multilots", json=_payload(mid, lots)
    )
    assert r.status_code == 200, r.text
    a, b = r.json()["lots"]
    assert a["paroi_mm"] == 20 and a["diametre_depart_mm"] == 76 + 40
    assert b["paroi_mm"] == 0 and b["diametre_depart_mm"] == 76
    assert (
        a["rebobinage"]["bobines"]["nb_bobines"]
        >= b["rebobinage"]["bobines"]["nb_bobines"]
    )


def test_apply_idempotent_remplace():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        did = _create_devis(db, numero="TEST-RBML-IDEM")

    p1 = _payload(mid, [_lot(epaisseur_saisie_um="60")])
    p2 = _payload(mid, [_lot(epaisseur_saisie_um="60"), _lot(epaisseur_saisie_um="60")])
    assert _http.post(f"/api/devis/{did}/rebobinage-multilots", json=p1).status_code == 200
    r2 = _http.post(f"/api/devis/{did}/rebobinage-multilots", json=p2)
    assert r2.status_code == 200
    with SessionLocal() as db:
        devis = db.get(Devis, did)
        assert devis.payload_output["rebobinage_multilots"]["nb_lots"] == 2


def test_apply_delete_retire_la_ligne():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        did = _create_devis(db, numero="TEST-RBML-DEL")

    _http.post(
        f"/api/devis/{did}/rebobinage-multilots",
        json=_payload(mid, [_lot(epaisseur_saisie_um="60")]),
    )
    r = _http.delete(f"/api/devis/{did}/rebobinage-multilots")
    assert r.status_code == 204
    with SessionLocal() as db:
        devis = db.get(Devis, did)
        assert "rebobinage_multilots" not in (devis.payload_output or {})
    # Idempotent : 2e DELETE reste 204.
    assert _http.delete(f"/api/devis/{did}/rebobinage-multilots").status_code == 204


def test_apply_devis_hors_tenant_404(as_user_b):
    with SessionLocal() as db:
        mid = _create_machine(db)
        did = _create_devis(db, numero="TEST-RBML-TENANT")
    # user B (tenant 2) tente d'appliquer sur un devis tenant 1 → 404.
    r = _http.post(
        f"/api/devis/{did}/rebobinage-multilots",
        json=_payload(mid, [_lot(epaisseur_saisie_um="60")]),
    )
    assert r.status_code == 404
