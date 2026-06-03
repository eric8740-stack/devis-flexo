"""Tests router rebobinage — Sprint 16 Lot C.

Couvre :
  - POST /api/rebobinage/calculer (preview, sans persistance)
  - POST /api/devis/{id}/rebobinage (apply — ligne additive payload_output)
  - DELETE /api/devis/{id}/rebobinage (retire la ligne)

Sacrés (à chaque commit) :
  - bug #6 6.2e-final : `devis.ht_total_eur` = BASE cost_engine +
    coût rebobinage. La BASE `payload_output["prix_vente_ht_eur"]` (valeur
    PURE cost_engine) reste EXACTE après apply rebobinage — c'est elle qui
    est sacrée, pas le total. `ht_total_eur` reflète désormais le coût total
    (base + rebobinage).
  - V1a 1449,09 € / V1b / V7a EXACT préservés (test_cost_engine_5cas_*),
    asserts sur fixture cost_engine découplée (sans rebobinage).
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.services.devis_total import ht_total_avec_rebobinage
from app.models import (
    Devis,
    MachineRebobineuse,
    ParametreMandrin,
)


_http = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_machine_rebobineuse(
    db: Session,
    entreprise_id: int = 1,
    nom: str = "Test Rebob Router",
    cout_horaire_eur: Decimal = Decimal("45.00"),
) -> MachineRebobineuse:
    mach = MachineRebobineuse(
        entreprise_id=entreprise_id,
        nom=nom,
        marque="MarqueTest",
        modele="RT100",
        laize_max_mm=Decimal("250"),
        diametre_max_mm=500,
        mandrins_supportes=[25, 38, 76, 152],
        vitesse_pratique_m_min=80,
        cout_horaire_eur=cout_horaire_eur,
        temps_changement_bobine_min=Decimal("1.50"),
        options=[],
        actif=True,
    )
    db.add(mach)
    db.commit()
    db.refresh(mach)
    return mach


def _ensure_parametre_mandrin(
    db: Session, entreprise_id: int = 1, scie_disponible: bool = True
) -> ParametreMandrin:
    """Crée ou UPDATE la row parametre_mandrin du tenant. Idempotent."""
    row = db.query(ParametreMandrin).filter_by(entreprise_id=entreprise_id).first()
    if row is None:
        row = ParametreMandrin(
            entreprise_id=entreprise_id,
            scie_disponible=scie_disponible,
            mode_par_defaut="auto",
        )
        db.add(row)
    else:
        row.scie_disponible = scie_disponible
    db.commit()
    db.refresh(row)
    return row


def _create_devis(
    db: Session, numero: str = "TEST-RB-001"
) -> Devis:
    """Crée un Devis minimal avec ht_total_eur fixe pour vérifier
    qu'il reste inchangé après application rebobinage."""
    devis = Devis(
        entreprise_id=1,
        numero=numero,
        payload_input={"machine_id": 1, "format_h_mm": 80, "format_l_mm": 100},
        payload_output={
            "prix_vente_ht_eur": "1449.09",
            "lignes": {"matiere": "100.00", "cliches": "200.00"},
        },
        mode_calcul="manuel",
        ht_total_eur=Decimal("1449.09"),  # valeur sacrée V1a EXACT
        format_h_mm=80,
        format_l_mm=100,
        machine_id=1,
    )
    db.add(devis)
    db.commit()
    db.refresh(devis)
    return devis


def _payload_calcul_typique(
    machine_id: int,
    mode: str = "auto",
    motif_force: str | None = None,
    nb_etiquettes: int = 10000,
    diametre_mandrin_mm: int = 76,
    diametre_max_bobine_mm: int = 226,
    nb_etiq_fixe: int | None = None,
) -> dict:
    return {
        "spec_lot": {
            "nb_etiquettes_total": nb_etiquettes,
            "intervalle_developpe_mm": "80",
            "epaisseur_matiere_mm": "0.06",
        },
        "profil_client": {
            "diametre_mandrin_mm": diametre_mandrin_mm,
            "diametre_max_bobine_mm": diametre_max_bobine_mm,
            "nb_etiq_par_bobine_fixe": nb_etiq_fixe,
        },
        "machine_rebobineuse_id": machine_id,
        "tarifs_mandrins": {
            "prix_pre_coupe_par_mandrin_eur": "5",
            "cout_decoupe_interne_par_mandrin_eur": "2",
            "cout_fixe_decoupe_interne_eur": "39",
        },
        "mode": mode,
        "motif_force": motif_force,
    }


# ---------------------------------------------------------------------------
# POST /api/rebobinage/calculer — preview
# ---------------------------------------------------------------------------


def test_calculer_preview_happy_path():
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Daco preview")
        _ensure_parametre_mandrin(db, scie_disponible=True)
        machine_id = mach.id

    r = _http.post(
        "/api/rebobinage/calculer",
        json=_payload_calcul_typique(machine_id=machine_id, nb_etiq_fixe=2500),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["machine_rebobineuse_id"] == machine_id
    assert data["bobines"]["nb_bobines"] == 4  # 10 000 / 2500
    # 4 bobines < seuil 13 → pre_coupe optimal
    assert data["arbitrage"]["mode_optimal"] == "pre_coupe"
    assert data["arbitrage"]["mode_applique"] == "pre_coupe"
    assert Decimal(data["cout_total_rebobinage_eur"]) > 0


def test_calculer_preview_machine_inexistante_404():
    r = _http.post(
        "/api/rebobinage/calculer",
        json=_payload_calcul_typique(machine_id=999999),
    )
    assert r.status_code == 404


def test_calculer_preview_machine_autre_tenant_404(as_user_b):
    """User A crée une machine, user B essaie de calculer avec → 404."""
    # Mais ici la fixture as_user_b override l'auth — donc les ops DB
    # tournent tjs avec session brute (pas scope auth). On crée une
    # machine pour tenant 1, user B (tenant 2) tente le calcul → 404.
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, entreprise_id=1)
        machine_id = mach.id

    r = _http.post(
        "/api/rebobinage/calculer",
        json=_payload_calcul_typique(machine_id=machine_id),
    )
    assert r.status_code == 404


def test_calculer_preview_mode_force_sans_motif_422():
    """À 4 bobines, optimal = pre_coupe. Forcer decoupe_interne sans
    motif → 422 (RebobinageError mappée en 422)."""
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Test mode forcé")
        _ensure_parametre_mandrin(db, scie_disponible=True)
        machine_id = mach.id

    r = _http.post(
        "/api/rebobinage/calculer",
        json=_payload_calcul_typique(
            machine_id=machine_id,
            mode="decoupe_interne",
            motif_force=None,
            nb_etiq_fixe=2500,  # 4 bobines, optimal pre_coupe
        ),
    )
    assert r.status_code == 422
    assert "motif_force" in r.json()["detail"].lower()


def test_calculer_preview_input_invalide_422():
    """Dmax ≤ Dmandrin → ValueError du moteur, mappée en 422."""
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Test input invalide")
        _ensure_parametre_mandrin(db, scie_disponible=True)
        machine_id = mach.id

    r = _http.post(
        "/api/rebobinage/calculer",
        json=_payload_calcul_typique(
            machine_id=machine_id,
            diametre_mandrin_mm=300,
            diametre_max_bobine_mm=200,  # Dmax < Dmandrin
        ),
    )
    assert r.status_code == 422
    assert "diametre" in r.json()["detail"].lower()


def test_calculer_preview_scie_indispo_force_decoupe_422():
    """Scie indispo + decoupe_interne forcé → 422 du moteur."""
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Test scie indispo")
        _ensure_parametre_mandrin(db, scie_disponible=False)
        machine_id = mach.id

    r = _http.post(
        "/api/rebobinage/calculer",
        json=_payload_calcul_typique(
            machine_id=machine_id,
            mode="decoupe_interne",
            motif_force="test",
        ),
    )
    assert r.status_code == 422
    assert "scie" in r.json()["detail"].lower()


def test_calculer_preview_sans_parametre_mandrin_defaults_safe():
    """Si parametre_mandrin n'existe pas pour le tenant, le router
    utilise des defaults défensifs (scie_disponible=False, auto)."""
    with SessionLocal() as db:
        # Purge explicite pour reproduire le cas DB sans seed
        db.query(ParametreMandrin).filter_by(entreprise_id=1).delete()
        db.commit()
        mach = _create_machine_rebobineuse(db, nom="Test sans params")
        machine_id = mach.id

    r = _http.post(
        "/api/rebobinage/calculer",
        json=_payload_calcul_typique(machine_id=machine_id, nb_etiq_fixe=2500),
    )
    assert r.status_code == 200, r.text
    # Mode "auto" sans scie → applique pre_coupe (rétrogradation possible
    # mais à 4 bobines pre_coupe est de toute façon optimal).
    assert r.json()["arbitrage"]["mode_applique"] == "pre_coupe"


# ---------------------------------------------------------------------------
# POST /api/devis/{id}/rebobinage — application
# ---------------------------------------------------------------------------


def test_apply_rebobinage_devis_persiste_payload_output():
    """Vérifie que la ligne rebobinage est bien stockée dans payload_output.

    bug #6 6.2e-final : `ht_total_eur` = base cost_engine + coût rebobinage
    (mono-lot fallback). La BASE `payload_output["prix_vente_ht_eur"]` reste
    EXACTE (1449,09 € = valeur PURE cost_engine, sacrée)."""
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Daco apply")
        _ensure_parametre_mandrin(db, scie_disponible=True)
        devis = _create_devis(db, numero="TEST-RB-APPLY-001")
        machine_id = mach.id
        devis_id = devis.id

    r = _http.post(
        f"/api/devis/{devis_id}/rebobinage",
        json=_payload_calcul_typique(machine_id=machine_id, nb_etiq_fixe=2500),
    )
    assert r.status_code == 200, r.text
    rebob = Decimal(r.json()["cout_total_rebobinage_eur"])
    assert rebob > 0

    with SessionLocal() as db:
        d = db.query(Devis).filter_by(id=devis_id).one()
        # BASE cost_engine PURE inchangée (sacré).
        assert d.payload_output["prix_vente_ht_eur"] == "1449.09"
        # ht_total = base + coût rebobinage (mono-lot fallback), via le helper.
        assert d.ht_total_eur == ht_total_avec_rebobinage(
            Decimal("1449.09"), d.payload_output
        )
        assert d.ht_total_eur > Decimal("1449.09")
        # La ligne rebobinage est dans payload_output
        rebobinage = d.payload_output["rebobinage"]
        assert rebobinage["applique"] is True
        assert rebobinage["machine_rebobineuse_id"] == machine_id
        assert rebobinage["mode_applique"] == "pre_coupe"
        assert Decimal(rebobinage["cout_total_rebobinage_eur"]) > 0
        # Détails complets persistés
        assert rebobinage["details"]["bobines"]["nb_bobines"] == 4


def test_apply_rebobinage_devis_idempotent_remplace_ligne():
    """Un 2e POST remplace la ligne précédente sans dupliquer."""
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Daco idempotent")
        _ensure_parametre_mandrin(db, scie_disponible=True)
        devis = _create_devis(db, numero="TEST-RB-IDEMP-001")
        machine_id = mach.id
        devis_id = devis.id

    # 1er apply — petite série
    r1 = _http.post(
        f"/api/devis/{devis_id}/rebobinage",
        json=_payload_calcul_typique(
            machine_id=machine_id, nb_etiquettes=5000, nb_etiq_fixe=2500
        ),
    )
    assert r1.status_code == 200
    nb_bobines_1 = r1.json()["bobines"]["nb_bobines"]
    assert nb_bobines_1 == 2

    # 2e apply — grosse série, doit REMPLACER (pas dupliquer)
    r2 = _http.post(
        f"/api/devis/{devis_id}/rebobinage",
        json=_payload_calcul_typique(
            machine_id=machine_id, nb_etiquettes=50000, nb_etiq_fixe=1000
        ),
    )
    assert r2.status_code == 200
    nb_bobines_2 = r2.json()["bobines"]["nb_bobines"]
    assert nb_bobines_2 == 50

    with SessionLocal() as db:
        d = db.query(Devis).filter_by(id=devis_id).one()
        # 1 seule clé "rebobinage", contenant le DERNIER résultat
        assert d.payload_output["rebobinage"]["details"]["bobines"]["nb_bobines"] == 50


def test_apply_rebobinage_devis_inexistant_404():
    r = _http.post(
        "/api/devis/999999/rebobinage",
        json=_payload_calcul_typique(machine_id=1),
    )
    assert r.status_code == 404


def test_apply_rebobinage_devis_autre_tenant_404(as_user_b):
    """User B ne peut pas apply rebobinage sur un devis tenant 1."""
    with SessionLocal() as db:
        devis = _create_devis(db, numero="TEST-RB-ISO-001")
        mach = _create_machine_rebobineuse(db, nom="Test iso")
        devis_id = devis.id
        machine_id = mach.id

    r = _http.post(
        f"/api/devis/{devis_id}/rebobinage",
        json=_payload_calcul_typique(machine_id=machine_id),
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/devis/{id}/rebobinage — retire
# ---------------------------------------------------------------------------


def test_delete_rebobinage_devis_retire_ligne():
    """Apply puis DELETE → payload_output.rebobinage absent."""
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Test delete")
        _ensure_parametre_mandrin(db, scie_disponible=True)
        devis = _create_devis(db, numero="TEST-RB-DEL-001")
        machine_id = mach.id
        devis_id = devis.id

    # Apply d'abord
    r1 = _http.post(
        f"/api/devis/{devis_id}/rebobinage",
        json=_payload_calcul_typique(machine_id=machine_id, nb_etiq_fixe=2500),
    )
    assert r1.status_code == 200

    # DELETE
    r2 = _http.delete(f"/api/devis/{devis_id}/rebobinage")
    assert r2.status_code == 204

    with SessionLocal() as db:
        d = db.query(Devis).filter_by(id=devis_id).one()
        assert "rebobinage" not in (d.payload_output or {})


def test_delete_rebobinage_devis_idempotent_si_absente():
    """DELETE sans ligne préalable → 204 sans erreur."""
    with SessionLocal() as db:
        devis = _create_devis(db, numero="TEST-RB-DEL-NOOP-001")
        devis_id = devis.id

    r = _http.delete(f"/api/devis/{devis_id}/rebobinage")
    assert r.status_code == 204

    with SessionLocal() as db:
        d = db.query(Devis).filter_by(id=devis_id).one()
        assert "rebobinage" not in (d.payload_output or {})


def test_delete_rebobinage_devis_autre_tenant_404(as_user_b):
    with SessionLocal() as db:
        devis = _create_devis(db, numero="TEST-RB-DEL-ISO-001")
        devis_id = devis.id

    r = _http.delete(f"/api/devis/{devis_id}/rebobinage")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Sacred V1a EXACT préservé
# ---------------------------------------------------------------------------


def test_apply_rebobinage_base_cost_engine_sacree_inchangee():
    """bug #6 6.2e-final : apply rebobinage à un devis V1a → la BASE
    cost_engine (`payload_output["prix_vente_ht_eur"]`) reste EXACTEMENT
    1449,09 € (sacré), tandis que `ht_total_eur` = base + coût rebobinage
    (le rebobinage entre désormais dans le total, fallback mono-lot)."""
    with SessionLocal() as db:
        mach = _create_machine_rebobineuse(db, nom="Sacred V1a")
        _ensure_parametre_mandrin(db, scie_disponible=True)
        devis = _create_devis(db, numero="TEST-RB-SACRED-V1A-001")
        assert devis.ht_total_eur == Decimal("1449.09")
        devis_id = devis.id
        machine_id = mach.id

    r = _http.post(
        f"/api/devis/{devis_id}/rebobinage",
        json=_payload_calcul_typique(machine_id=machine_id, nb_etiq_fixe=1000),
    )
    assert r.status_code == 200
    rebob = Decimal(r.json()["cout_total_rebobinage_eur"])
    assert rebob > 0  # garde-fou : on teste bien un ajout effectif

    with SessionLocal() as db:
        d = db.query(Devis).filter_by(id=devis_id).one()
        # BASE cost_engine PURE inchangée (sacré).
        assert d.payload_output["prix_vente_ht_eur"] == "1449.09"
        # ht_total = base + coût rebobinage (via le helper, arrondi money).
        assert d.ht_total_eur == ht_total_avec_rebobinage(
            Decimal("1449.09"), d.payload_output
        )
        assert d.ht_total_eur > Decimal("1449.09")
        # Rebobinage stocké à côté
        assert d.payload_output["rebobinage"]["applique"] is True
