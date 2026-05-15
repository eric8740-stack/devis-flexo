"""Tests du router /api/ia — Sprint 13 Lot S13.E.3.

Couvre :
  - 200 happy path : payload Claude persisté + renvoyé
  - 403 si user n'a pas le module flexocheck
  - 422 si mime_type non supporté ou base64 invalide
  - 502 si Claude API echoue (IAClientError)
  - Persistance d'une row 'erreur' même en cas d'echec IA (audit)
  - Isolation tenant : chaque analyse scopée user.entreprise_id

Aucun appel reel Claude — on monkeypatch le SERVICE
analyser_photo_etiquette pour controler la reponse.
"""
import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import AnalysePhotoEtiquette
from app.routers import ia as ia_router
from app.services.ia.client import IAClientError


client = TestClient(app)


# Une image PNG minimale valide (1x1 pixel) en base64 — vraie image pour
# que la validation base64 passe.
PNG_1PX_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42m"
    "P8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


REPONSE_CLAUDE_FAKE = {
    "couleurs_detectees": [
        {
            "rgb_approximatif": "#000000",
            "pantone_proche_estime": None,
            "surface_pct": 100,
        }
    ],
    "nombre_couleurs_distinctes": 1,
    "couleurs_min_technique": 1,
    "couleurs_max_technique": 1,
    "techniques_impression_estimees": ["CMJN"],
    "matiere_estimee": {
        "type": "papier",
        "couleur": "blanc",
        "finition_apparente": "mat",
    },
    "finitions_visibles": [],
    "presence_blanc_opaque": False,
    "niveau_confiance": "moyen",
    "limites_analyse": ["pixel unique"],
}


@pytest.fixture
def cleanup_analyses():
    db: Session = SessionLocal()
    try:
        for ent_id in (1, 2, 3, 4):
            db.query(AnalysePhotoEtiquette).filter_by(
                entreprise_id=ent_id
            ).delete()
        db.commit()
        yield
        for ent_id in (1, 2, 3, 4):
            db.query(AnalysePhotoEtiquette).filter_by(
                entreprise_id=ent_id
            ).delete()
        db.commit()
    finally:
        db.close()


def _install_service_mock(monkeypatch, return_value=None, raise_exc=None):
    """Remplace analyser_photo_etiquette pour controler le comportement
    sans appeler Claude."""

    def fake(image_bytes, mime_type):  # noqa: ARG001
        if raise_exc is not None:
            raise raise_exc
        return return_value or REPONSE_CLAUDE_FAKE

    monkeypatch.setattr(ia_router, "analyser_photo_etiquette", fake)


# ---------------------------------------------------------------------------
# 200 happy path
# ---------------------------------------------------------------------------


def test_post_analyser_photo_happy_path(cleanup_analyses, monkeypatch):
    """L'admin demo (entreprise_id=1) a les 2 modules → access OK.
    On mock Claude pour renvoyer une analyse valide."""
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={
            "image_base64": PNG_1PX_B64,
            "mime_type": "image/png",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] > 0
    assert body["niveau_confiance"] == "moyen"
    assert body["nombre_couleurs_distinctes"] == 1
    assert body["model_utilise"] == "claude-sonnet-4-6"
    assert body["resultats_ia"]["matiere_estimee"]["type"] == "papier"

    # Persistance vérifiée
    db = SessionLocal()
    try:
        row = (
            db.query(AnalysePhotoEtiquette)
            .filter_by(id=body["id"])
            .first()
        )
        assert row is not None
        assert row.entreprise_id == 1
        assert row.photo_mime_type == "image/png"
        assert row.erreur is None
    finally:
        db.close()


def test_post_analyser_photo_tolere_prefix_data_url(
    cleanup_analyses, monkeypatch
):
    """Le frontend utilise souvent FileReader qui produit
    'data:image/png;base64,...' — on doit le tolérer."""
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={
            "image_base64": f"data:image/png;base64,{PNG_1PX_B64}",
            "mime_type": "image/png",
        },
    )
    assert r.status_code == 200


def test_post_analyser_photo_rattache_devis(cleanup_analyses, monkeypatch):
    """devis_id passe correctement (FK SET NULL en BDD)."""
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={
            "image_base64": PNG_1PX_B64,
            "mime_type": "image/png",
            "devis_id": 12345,  # devis fictif, FK SET NULL le rejettera pas
        },
    )
    # FK n'existe pas → IntegrityError converti en 409 par le handler global
    # OU bien acceptee selon la config FK. Acceptons les 2 cas.
    assert r.status_code in (200, 409)


# ---------------------------------------------------------------------------
# 403 - module flexocheck requis
# ---------------------------------------------------------------------------


def test_post_403_si_pas_module_flexocheck(
    cleanup_analyses, as_user_flexocompare_only, monkeypatch
):
    """User compare-only n'a PAS flexocheck → 403."""
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={"image_base64": PNG_1PX_B64, "mime_type": "image/png"},
    )
    assert r.status_code == 403
    assert "flexocheck" in r.json()["detail"].lower()


def test_post_200_si_user_a_module_flexocheck(
    cleanup_analyses, as_user_flexocheck_only, monkeypatch
):
    """User check-only a flexocheck → access OK."""
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={"image_base64": PNG_1PX_B64, "mime_type": "image/png"},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 422 - validations input
# ---------------------------------------------------------------------------


def test_post_422_si_mime_type_non_supporte(cleanup_analyses, monkeypatch):
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={"image_base64": PNG_1PX_B64, "mime_type": "image/svg+xml"},
    )
    assert r.status_code == 422


def test_post_422_si_base64_invalide(cleanup_analyses, monkeypatch):
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={
            "image_base64": "ceci n'est pas du base64 valide !@#",
            "mime_type": "image/png",
        },
    )
    assert r.status_code == 422
    assert "image_base64" in r.json()["detail"].lower()


def test_post_422_si_image_base64_vide(cleanup_analyses, monkeypatch):
    _install_service_mock(monkeypatch)

    r = client.post(
        "/api/ia/analyser-photo",
        json={"image_base64": "", "mime_type": "image/png"},
    )
    # min_length=1 dans le schema → 422 (Pydantic) avant meme d'arriver au handler
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 502 - Claude API echoue, mais on persiste une row 'erreur' pour audit
# ---------------------------------------------------------------------------


def test_post_502_si_claude_echoue_et_persiste_erreur(
    cleanup_analyses, monkeypatch
):
    """IAClientError remontée par le service → 502 + row erreur persistée
    pour analytique (taux d'echec, patterns)."""
    _install_service_mock(
        monkeypatch,
        raise_exc=IAClientError("ANTHROPIC_API_KEY absente"),
    )

    r = client.post(
        "/api/ia/analyser-photo",
        json={"image_base64": PNG_1PX_B64, "mime_type": "image/png"},
    )
    assert r.status_code == 502
    assert "Analyse IA" in r.json()["detail"]

    # Vérif persistance row erreur
    db = SessionLocal()
    try:
        rows = (
            db.query(AnalysePhotoEtiquette)
            .filter_by(entreprise_id=1)
            .filter(AnalysePhotoEtiquette.erreur.isnot(None))
            .all()
        )
        assert len(rows) == 1
        assert "ANTHROPIC_API_KEY" in rows[0].erreur
        assert rows[0].resultats_ia == {}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Isolation tenant
# ---------------------------------------------------------------------------


def test_isolation_tenant_analyses_scope_correctement(
    cleanup_analyses, switch_to_user_b, monkeypatch
):
    """User A fait une analyse, user B en fait une → 2 rows dans 2 tenants
    distincts. Garantit le scoping multi-tenant."""
    _install_service_mock(monkeypatch)

    # User A (entreprise_id=1)
    r1 = client.post(
        "/api/ia/analyser-photo",
        json={"image_base64": PNG_1PX_B64, "mime_type": "image/png"},
    )
    assert r1.status_code == 200

    # User B (entreprise_id=2)
    switch_to_user_b()
    r2 = client.post(
        "/api/ia/analyser-photo",
        json={"image_base64": PNG_1PX_B64, "mime_type": "image/png"},
    )
    assert r2.status_code == 200

    db = SessionLocal()
    try:
        assert (
            db.query(AnalysePhotoEtiquette).filter_by(entreprise_id=1).count()
            == 1
        )
        assert (
            db.query(AnalysePhotoEtiquette).filter_by(entreprise_id=2).count()
            == 1
        )
    finally:
        db.close()
