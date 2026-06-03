"""Tests bug #6 6.2e-final — ht_total consomme le coût rebobinage.

`devis.ht_total_eur` = BASE cost_engine (`payload_output["prix_vente_ht_eur"]`,
inchangée = sacré) + contribution rebobinage (multilots prioritaire, mono-lot
fallback, sinon 0).

Niveaux :
  - unitaire : helper pur `devis_total` ;
  - endpoint : priorité multilots > mono, retour à la base au DELETE.
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Devis, MachineRebobineuse, ParametreMandrin
from app.services.devis_total import (
    contribution_rebobinage_eur,
    ht_total_avec_rebobinage,
)


_http = TestClient(app)


# ---------------------------------------------------------------------------
# Unitaire — helper pur
# ---------------------------------------------------------------------------


def test_contribution_aucune_ligne_zero():
    assert contribution_rebobinage_eur(None) == Decimal("0")
    assert contribution_rebobinage_eur({}) == Decimal("0")


def test_contribution_mono_lot_fallback():
    po = {"rebobinage": {"applique": True, "cout_total_rebobinage_eur": "12.50"}}
    assert contribution_rebobinage_eur(po) == Decimal("12.50")


def test_contribution_multilots_prioritaire_sur_mono():
    po = {
        "rebobinage": {"applique": True, "cout_total_rebobinage_eur": "12.50"},
        "rebobinage_multilots": {
            "applique": True,
            "cout_total_rebobinage_eur": "31.00",
        },
    }
    assert contribution_rebobinage_eur(po) == Decimal("31.00")


def test_contribution_ignore_ligne_non_appliquee():
    po = {"rebobinage": {"applique": False, "cout_total_rebobinage_eur": "12.50"}}
    assert contribution_rebobinage_eur(po) == Decimal("0")


def test_ht_total_base_none_reste_none():
    """Chiffrage incomplet (base None) → on n'invente pas de total."""
    po = {"rebobinage_multilots": {"applique": True, "cout_total_rebobinage_eur": "5"}}
    assert ht_total_avec_rebobinage(None, po) is None


def test_ht_total_base_plus_contribution():
    po = {"rebobinage_multilots": {"applique": True, "cout_total_rebobinage_eur": "31.00"}}
    assert ht_total_avec_rebobinage(Decimal("1449.09"), po) == Decimal("1480.09")


# ---------------------------------------------------------------------------
# Endpoint — priorité + retour à la base
# ---------------------------------------------------------------------------


def _create_machine(db) -> int:
    mach = MachineRebobineuse(
        entreprise_id=1, nom="Rebob 62e final", marque="M", modele="RT",
        laize_max_mm=Decimal("250"), diametre_max_mm=500,
        mandrins_supportes=[25, 38, 76, 152], vitesse_pratique_m_min=80,
        cout_horaire_eur=Decimal("45.00"),
        temps_changement_bobine_min=Decimal("1.50"), options=[], actif=True,
    )
    db.add(mach)
    db.commit()
    db.refresh(mach)
    return mach.id


def _set_paroi(db, paroi_mm) -> None:
    row = db.query(ParametreMandrin).filter_by(entreprise_id=1).first()
    if row is None:
        row = ParametreMandrin(entreprise_id=1, scie_disponible=True,
                               mode_par_defaut="auto", epaisseur_paroi_mm=paroi_mm)
        db.add(row)
    else:
        row.epaisseur_paroi_mm = paroi_mm
    db.commit()


def _create_devis(db, numero, ht="1449.09") -> int:
    devis = Devis(
        entreprise_id=1, numero=numero,
        payload_input={"machine_id": 1, "format_h_mm": 80, "format_l_mm": 100},
        payload_output={"prix_vente_ht_eur": ht},
        mode_calcul="manuel", ht_total_eur=Decimal(ht),
        format_h_mm=80, format_l_mm=100, machine_id=1,
    )
    db.add(devis)
    db.commit()
    db.refresh(devis)
    return devis.id


def _lot(**kw) -> dict:
    base = {
        "nb_etiquettes_total": 10000, "intervalle_developpe_mm": "80",
        "diametre_mandrin_mm": 76, "diametre_max_bobine_mm": 300,
        "nb_etiq_par_bobine_fixe": None, "matiere_id": None,
        "epaisseur_saisie_um": "60", "paroi_override_mm": None,
    }
    base.update(kw)
    return base


def _payload_ml(mid, lots) -> dict:
    return {
        "lots": lots, "machine_rebobineuse_id": mid,
        "tarifs_mandrins": {"prix_pre_coupe_par_mandrin_eur": "5",
                            "cout_decoupe_interne_par_mandrin_eur": "2",
                            "cout_fixe_decoupe_interne_eur": "39"},
        "mode": "auto", "motif_force": None,
    }


def _payload_mono(mid) -> dict:
    return {
        "spec_lot": {"nb_etiquettes_total": 10000, "intervalle_developpe_mm": "80",
                     "epaisseur_matiere_mm": "0.06"},
        "profil_client": {"diametre_mandrin_mm": 76, "diametre_max_bobine_mm": 300,
                          "nb_etiq_par_bobine_fixe": None},
        "machine_rebobineuse_id": mid,
        "tarifs_mandrins": {"prix_pre_coupe_par_mandrin_eur": "5",
                            "cout_decoupe_interne_par_mandrin_eur": "2",
                            "cout_fixe_decoupe_interne_eur": "39"},
        "mode": "auto", "motif_force": None,
    }


def test_multilots_prioritaire_sur_mono_dans_ht_total():
    """Mono puis multilots appliqués → ht_total = base + MULTILOTS (pas la
    somme des deux)."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi(db, None)
        did = _create_devis(db, "TEST-62EF-PRIO")

    r_mono = _http.post(f"/api/devis/{did}/rebobinage", json=_payload_mono(mid))
    assert r_mono.status_code == 200
    r_ml = _http.post(f"/api/devis/{did}/rebobinage-multilots",
                      json=_payload_ml(mid, [_lot(), _lot()]))
    assert r_ml.status_code == 200
    agg = Decimal(r_ml.json()["cout_total_rebobinage_eur"])

    with SessionLocal() as db:
        d = db.get(Devis, did)
        assert d.payload_output["prix_vente_ht_eur"] == "1449.09"
        # multilots prioritaire (pas +mono) ; via helper pour l'arrondi money.
        assert d.ht_total_eur == ht_total_avec_rebobinage(
            Decimal("1449.09"), d.payload_output
        )
        # Effectivement la contribution multilots (et pas la mono).
        assert d.ht_total_eur == ht_total_avec_rebobinage(
            Decimal("1449.09"),
            {"rebobinage_multilots": {"applique": True,
                                      "cout_total_rebobinage_eur": str(agg)}},
        )


def test_delete_multilots_retombe_sur_mono_puis_base():
    """DELETE multilots → ht_total retombe sur la contribution mono ; DELETE
    mono → ht_total = base pure."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi(db, None)
        did = _create_devis(db, "TEST-62EF-DEL")

    r_mono = _http.post(f"/api/devis/{did}/rebobinage", json=_payload_mono(mid))
    mono = Decimal(r_mono.json()["cout_total_rebobinage_eur"])
    _http.post(f"/api/devis/{did}/rebobinage-multilots",
               json=_payload_ml(mid, [_lot()]))

    # DELETE multilots → fallback sur la ligne mono encore présente.
    assert _http.delete(f"/api/devis/{did}/rebobinage-multilots").status_code == 204
    with SessionLocal() as db:
        d = db.get(Devis, did)
        assert "rebobinage_multilots" not in d.payload_output
        assert d.ht_total_eur == ht_total_avec_rebobinage(
            Decimal("1449.09"), d.payload_output
        )
        assert d.ht_total_eur > Decimal("1449.09")  # mono contribue encore
        assert mono > 0

    # DELETE mono → base pure (aucune contribution).
    assert _http.delete(f"/api/devis/{did}/rebobinage").status_code == 204
    with SessionLocal() as db:
        d = db.get(Devis, did)
        assert d.ht_total_eur == Decimal("1449.09")
