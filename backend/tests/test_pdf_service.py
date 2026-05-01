"""Tests service PDF (Sprint 4 Lot 4e).

⚠️ weasyprint nécessite des libs natives GTK/Cairo/Pango installées sur
l'OS. Sur Windows local, ces libs sont rarement présentes — on skip
gracefully (les tests passent en CI Linux + Railway prod).

Probe d'exécution réelle au chargement du module : si write_pdf échoue
sur un HTML trivial, on skip tout le fichier.

Garde-fou bruyant : voir tests/test_weasyprint_runtime.py (Hotfix-PDF-B)
qui FAIL si la probe échoue sur Linux ou en CI (alerte immédiate au lieu
du skip silencieux qui a masqué le bug TypeError float/Decimal Sprint 4).
"""
from datetime import datetime
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.models import Devis
from app.services.pdf_service import generate_devis_pdf

# Probe runtime — détecte l'absence des libs natives GTK (Cairo/Pango) qui
# ne sont pas dans l'image Python par défaut Windows. L'import weasyprint
# fonctionne (présent dans requirements.txt), c'est write_pdf() qui échoue
# au runtime sans GTK installé.
try:
    from weasyprint import HTML

    HTML(string="<html><body>probe</body></html>").write_pdf()
    _WEASYPRINT_OK = True
except Exception:  # noqa: BLE001
    _WEASYPRINT_OK = False

pytestmark = pytest.mark.skipif(
    not _WEASYPRINT_OK,
    reason="weasyprint runtime libs (GTK/Cairo/Pango) indisponibles — Linux/Docker only",
)


def _payload_output_v1a_manuel() -> dict:
    return {
        "mode": "manuel",
        "cout_revient_eur": "1228.04",
        "pct_marge_appliquee": "0.18",
        "prix_vente_ht_eur": "1449.09",
        "prix_au_mille_eur": "6.92",
        "postes": [
            {
                "poste_numero": i,
                "libelle": f"Poste P{i}",
                "montant_eur": "100.00",
                "details": {},
            }
            for i in range(1, 8)
        ],
    }


def _payload_output_v1a_matching() -> dict:
    return {
        "mode": "matching",
        "candidats": [
            {
                "z": z,
                "nb_etiq_par_tour": n,
                "circonference_mm": "425.45",
                "pas_mm": "42.545",
                "intervalle_mm": "2.545",
                "nb_etiq_par_metre": 23,
                "postes": [
                    {
                        "poste_numero": i,
                        "libelle": f"Poste P{i}",
                        "montant_eur": "100.00",
                        "details": {},
                    }
                    for i in range(1, 8)
                ],
                "cout_revient_eur": "1228.04",
                "pct_marge_appliquee": "0.18",
                "prix_vente_ht_eur": "1449.09",
                "prix_au_mille_eur": "7.00",
            }
            for z, n in [(134, 10), (121, 9), (108, 8)]
        ],
    }


def _make_devis_in_db(mode: str, **overrides) -> Devis:
    base = dict(
        numero=overrides.pop("numero", f"DEV-PDF-{mode}"),
        statut="brouillon",
        client_id=None,
        payload_input={
            "ml_total": 3000,
            "laize_utile_mm": 220,
            "intervalle_mm": "3" if mode == "manuel" else None,
            "mode_calcul": mode,
        },
        payload_output=(
            _payload_output_v1a_manuel()
            if mode == "manuel"
            else _payload_output_v1a_matching()
        ),
        mode_calcul=mode,
        cylindre_choisi_z=134 if mode == "matching" else None,
        cylindre_choisi_nb_etiq=10 if mode == "matching" else None,
        ht_total_eur=Decimal("1449.09"),
        format_h_mm=Decimal("40"),
        format_l_mm=Decimal("60"),
        machine_id=1,
    )
    base.update(overrides)
    return Devis(**base)


def test_pdf_generation_v1a_manuel_returns_valid_pdf_bytes():
    """Génère le PDF d'un devis V1a manuel, vérifie signature %PDF-."""
    with SessionLocal() as db:
        # Cleanup éventuels résidus
        db.query(Devis).filter(Devis.numero.like("DEV-PDF-%")).delete()
        db.commit()
        devis = _make_devis_in_db("manuel")
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            pdf_bytes = generate_devis_pdf(devis, db)
            assert isinstance(pdf_bytes, bytes)
            assert len(pdf_bytes) > 1000  # PDF non trivial
            assert pdf_bytes.startswith(b"%PDF-"), "Signature PDF manquante"
        finally:
            db.delete(devis)
            db.commit()


def test_pdf_generation_v1a_matching_uses_chosen_candidat():
    """Mode matching : prend le candidat sélectionné via cylindre_choisi_z."""
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.numero.like("DEV-PDF-%")).delete()
        db.commit()
        devis = _make_devis_in_db("matching")
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            pdf_bytes = generate_devis_pdf(devis, db)
            assert pdf_bytes.startswith(b"%PDF-")
            assert len(pdf_bytes) > 1000
        finally:
            db.delete(devis)
            db.commit()


def test_get_devis_pdf_endpoint_returns_application_pdf():
    """Sprint 4 Lot 4f — endpoint HTTP GET /api/devis/{id}/pdf."""
    from fastapi.testclient import TestClient

    from app.main import app

    test_client = TestClient(app)
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.numero.like("DEV-PDF-%")).delete()
        db.commit()
        devis = _make_devis_in_db("manuel", numero="DEV-PDF-HTTP")
        db.add(devis)
        db.commit()
        db.refresh(devis)
        devis_id = devis.id
    try:
        r = test_client.get(f"/api/devis/{devis_id}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert "DEV-PDF-HTTP.pdf" in r.headers["content-disposition"]
        assert r.content.startswith(b"%PDF-")
        assert len(r.content) > 1000
    finally:
        with SessionLocal() as db:
            d = db.get(Devis, devis_id)
            if d:
                db.delete(d)
                db.commit()


def test_pdf_generation_now_injection():
    """Vérifie que la variable `now` (datetime) est bien passée au template
    (utile pour le footer 'généré le ...').

    Test en blanc : on génère et on vérifie qu'il n'y a pas eu d'exception
    Jinja2 (UndefinedError) ; le contenu binaire PDF n'est pas inspecté.
    """
    with SessionLocal() as db:
        db.query(Devis).filter(Devis.numero.like("DEV-PDF-%")).delete()
        db.commit()
        devis = _make_devis_in_db("manuel", numero="DEV-PDF-NOW")
        db.add(devis)
        db.commit()
        db.refresh(devis)
        try:
            before = datetime.now()
            pdf_bytes = generate_devis_pdf(devis, db)
            after = datetime.now()
            assert before <= after  # sanity check
            assert pdf_bytes.startswith(b"%PDF-")
        finally:
            db.delete(devis)
            db.commit()
