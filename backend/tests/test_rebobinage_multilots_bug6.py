"""Tests bug #6 étape 6.2a — Ø sur vraies valeurs (épaisseur par lot + paroi),
1 Ø par lot.

Deux niveaux :
  - unitaire : résolveur partagé `diametre_resolver` (épaisseur matière/saisie/
    fallback ; Ø départ = mandrin + 2 × paroi, paroi NULL → 0 non-régressif) ;
  - endpoint : POST /api/rebobinage/calculer-multilots (1 résultat/lot, échos
    résolus, effet paroi sur nb bobines, isolation matière hors tenant).

Sacré : aucune formule géométrique touchée ; `bat_calculs` / `rotation_se`
intouchés. Le coût n'est pas affecté (preview, pas de cost_engine).
"""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import MachineRebobineuse, Matiere, ParametreMandrin
from app.services.diametre_resolver import (
    EPAISSEUR_FALLBACK_UM,
    resoudre_diametre_depart_mm,
    resoudre_epaisseur_um,
)


_http = TestClient(app)


# ---------------------------------------------------------------------------
# Unitaire — résolveur partagé (point de calcul unique)
# ---------------------------------------------------------------------------


def test_resoudre_epaisseur_priorite_matiere():
    val, source = resoudre_epaisseur_um(matiere_epaisseur_um=50, saisie_um=120)
    assert val == 50.0 and source == "matiere"


def test_resoudre_epaisseur_matiere_absente_utilise_saisie():
    val, source = resoudre_epaisseur_um(matiere_epaisseur_um=None, saisie_um=120)
    assert val == 120.0 and source == "saisie"


def test_resoudre_epaisseur_fallback_150():
    val, source = resoudre_epaisseur_um(matiere_epaisseur_um=None, saisie_um=None)
    assert val == EPAISSEUR_FALLBACK_UM == 150.0 and source == "fallback"


def test_resoudre_epaisseur_matiere_zero_tombe_sur_saisie():
    # Une épaisseur catalogue ≤ 0 est traitée comme absente.
    val, source = resoudre_epaisseur_um(matiere_epaisseur_um=0, saisie_um=90)
    assert val == 90.0 and source == "saisie"


def test_resoudre_diametre_depart_paroi_absente_non_regressif():
    depart, paroi = resoudre_diametre_depart_mm(mandrin_mm=76, paroi_mm=None)
    assert depart == 76 and paroi == 0  # Ø départ = mandrin (comportement actuel)


def test_resoudre_diametre_depart_paroi_ajoute_2x():
    depart, paroi = resoudre_diametre_depart_mm(mandrin_mm=76, paroi_mm=10)
    assert depart == 96 and paroi == 10  # 76 + 2×10


def test_resoudre_diametre_depart_override_prioritaire():
    depart, paroi = resoudre_diametre_depart_mm(
        mandrin_mm=76, paroi_mm=10, paroi_override_mm=3
    )
    assert depart == 82 and paroi == 3  # override 3 > tenant 10


# ---------------------------------------------------------------------------
# Helpers endpoint
# ---------------------------------------------------------------------------


def _create_machine(db, nom="Rebob multilots") -> int:
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
    """Pose epaisseur_paroi_mm sur le parametre_mandrin du tenant (idempotent)."""
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


def _lot(
    *,
    nb=10000,
    mandrin=76,
    dmax=300,
    matiere_id=None,
    epaisseur_saisie_um=None,
    paroi_override_mm=None,
    nb_etiq_fixe=None,
) -> dict:
    lot = {
        "nb_etiquettes_total": nb,
        "intervalle_developpe_mm": "80",
        "diametre_mandrin_mm": mandrin,
        "diametre_max_bobine_mm": dmax,
        "nb_etiq_par_bobine_fixe": nb_etiq_fixe,
        "matiere_id": matiere_id,
        "epaisseur_saisie_um": epaisseur_saisie_um,
        "paroi_override_mm": paroi_override_mm,
    }
    return lot


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
# Endpoint — épaisseur par lot
# ---------------------------------------------------------------------------


def test_epaisseur_source_matiere():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        mat = _create_matiere(db, "MULTILOT_50", 50)
    r = _http.post(
        "/api/rebobinage/calculer-multilots",
        json=_payload(mid, [_lot(matiere_id=mat)]),
    )
    assert r.status_code == 200, r.text
    lot0 = r.json()["lots"][0]
    assert lot0["epaisseur_effective_um"] == 50.0
    assert lot0["epaisseur_source"] == "matiere"


def test_epaisseur_matiere_null_utilise_saisie():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
        # Matière SANS épaisseur (colonne NULL) → on retombe sur la saisie.
        mat = _create_matiere(db, "MULTILOT_NULL", None)
    r = _http.post(
        "/api/rebobinage/calculer-multilots",
        json=_payload(mid, [_lot(matiere_id=mat, epaisseur_saisie_um="120")]),
    )
    assert r.status_code == 200, r.text
    lot0 = r.json()["lots"][0]
    assert lot0["epaisseur_effective_um"] == 120.0
    assert lot0["epaisseur_source"] == "saisie"


def test_epaisseur_fallback_150():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
    r = _http.post(
        "/api/rebobinage/calculer-multilots",
        json=_payload(mid, [_lot()]),  # ni matiere_id ni saisie
    )
    assert r.status_code == 200, r.text
    lot0 = r.json()["lots"][0]
    assert lot0["epaisseur_effective_um"] == 150.0
    assert lot0["epaisseur_source"] == "fallback"


def test_matiere_hors_tenant_404():
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
    r = _http.post(
        "/api/rebobinage/calculer-multilots",
        json=_payload(mid, [_lot(matiere_id=999999)]),
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Endpoint — paroi mandrin
# ---------------------------------------------------------------------------


def test_paroi_null_non_regressif():
    """Paroi NULL → Ø départ = Ø mandrin (comportement d'avant le fix)."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
    r = _http.post(
        "/api/rebobinage/calculer-multilots",
        json=_payload(mid, [_lot(mandrin=76, epaisseur_saisie_um="60")]),
    )
    assert r.status_code == 200, r.text
    lot0 = r.json()["lots"][0]
    assert lot0["paroi_mm"] == 0
    assert lot0["diametre_depart_mm"] == 76  # == mandrin


def test_paroi_renseignee_augmente_diametre_depart_et_bobines():
    """Paroi renseignée → Ø départ = mandrin + 2×paroi → moins de longueur
    enroulable → nb bobines ≥ cas sans paroi."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, 15)  # paroi tenant
    # Lot A : paroi tenant 15 → départ 76 + 30 = 106.
    # Lot B : override 0 → départ 76 (cas sans paroi), même géométrie sinon.
    lots = [
        _lot(mandrin=76, dmax=300, epaisseur_saisie_um="60"),
        _lot(mandrin=76, dmax=300, epaisseur_saisie_um="60", paroi_override_mm=0),
    ]
    r = _http.post(
        "/api/rebobinage/calculer-multilots", json=_payload(mid, lots)
    )
    assert r.status_code == 200, r.text
    a, b = r.json()["lots"]
    assert a["paroi_mm"] == 15 and a["diametre_depart_mm"] == 106
    assert b["paroi_mm"] == 0 and b["diametre_depart_mm"] == 76
    # Moins de matière enroulable avec paroi → bobines plus nombreuses (ou égal).
    assert (
        a["rebobinage"]["bobines"]["nb_bobines"]
        >= b["rebobinage"]["bobines"]["nb_bobines"]
    )


# ---------------------------------------------------------------------------
# Endpoint — 1 Ø par lot + cohérence
# ---------------------------------------------------------------------------


def test_un_diametre_par_lot():
    """N lots → N résultats, chacun avec son propre Ø départ."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, None)
    lots = [
        _lot(mandrin=76, epaisseur_saisie_um="60"),
        _lot(mandrin=152, epaisseur_saisie_um="60"),
    ]
    r = _http.post(
        "/api/rebobinage/calculer-multilots", json=_payload(mid, lots)
    )
    assert r.status_code == 200, r.text
    out = r.json()["lots"]
    assert len(out) == 2
    assert out[0]["diametre_depart_mm"] == 76
    assert out[1]["diametre_depart_mm"] == 152


def test_coherence_diametre_depart_echo():
    """Le Ø départ renvoyé = mandrin + 2×paroi (résolveur unique, même valeur
    que le Ø candidat)."""
    with SessionLocal() as db:
        mid = _create_machine(db)
        _set_paroi_tenant(db, 8)
    r = _http.post(
        "/api/rebobinage/calculer-multilots",
        json=_payload(mid, [_lot(mandrin=76, epaisseur_saisie_um="60")]),
    )
    assert r.status_code == 200, r.text
    lot0 = r.json()["lots"][0]
    assert lot0["mandrin_mm"] == 76
    assert lot0["paroi_mm"] == 8
    assert lot0["diametre_depart_mm"] == 76 + 2 * 8
