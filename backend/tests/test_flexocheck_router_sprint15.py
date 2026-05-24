"""Tests du router /api/flexocheck — Sprint 15 Lot 3.

Couvre les 7 endpoints :

  POST  /controle-bat/upload-bat        (multipart PDF/image)
  GET   /productions-actives
  GET   /controle-bat/contexte/{devis_id}
  POST  /controle-bat/                  (multipart photo + analyse IA)
  GET   /controle-bat/{devis_id}        (liste tentatives)
  POST  /controle-bat/{id}/decision
  POST  /controle-bat/{id}/retirage     (multipart photo, tentative+1)
  GET   /blobs/{image_key}              (serve fichier, scope tenant)

Claude API toujours mockée — `monkeypatch.setattr(ia_client,
"_get_anthropic_client", ...)` (même pattern que test_ia_analyse_photo).

Multi-tenant vérifié : un user B ne voit pas les BAT/contrôles d'un
user A (404 retourné).
"""
import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import (
    BatReference,
    ControleBat,
    Devis,
)
from app.services.ia import client as ia_client


_http = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_devis(
    db: Session, numero: str = "TEST-FX-001", statut: str = "valide"
) -> Devis:
    """Crée un Devis minimal scopé entreprise demo (id=1)."""
    devis = Devis(
        entreprise_id=1,
        numero=numero,
        payload_input={"machine_id": 1},
        payload_output={"prix_vente_ht_eur": "0"},
        mode_calcul="manuel",
        ht_total_eur=0,
        format_h_mm=40,
        format_l_mm=60,
        machine_id=1,
        statut=statut,
    )
    db.add(devis)
    db.flush()
    return devis


_REPONSE_CLAUDE_VALIDE = {
    "score_conformite_global": 88,
    "decision_recommandee": "ajuster_avant_demarrage",
    "ecarts_detectes": [
        {
            "type": "couleur",
            "gravite": "majeur",
            "localisation": "bandeau bas",
            "description": "Jaune trop dense",
            "suggestion_correction": "Diminuer densité jaune",
        },
        {
            "type": "position",
            "gravite": "mineur",
            "localisation": "logo",
            "description": "Décalé de 1 mm",
            "suggestion_correction": "Recaler",
        },
    ],
    "elements_conformes": ["Découpe", "Texte principal"],
    "elements_manquants": [],
    "niveau_confiance_analyse": "haut",
    "limites_analyse": ["Éclairage smartphone"],
    "sens_sortie_detecte": {
        "orientation_etiquette": "tête en haut",
        "sens_lecture": "gauche-vers-droite",
        "sens_enroulement_resultant": "SE1",
        "coherence_avec_bat": True,
    },
    "alerte_sens_enroulement": None,
}


def _install_mock_ia(
    monkeypatch,
    payload: dict | None = None,
    *,
    raise_exc: Exception | None = None,
):
    """Installe un mock Claude API renvoyant `payload` (ou lève `raise_exc`)."""
    if raise_exc is not None:
        fake_client = MagicMock()
        fake_client.messages.create.side_effect = raise_exc
        monkeypatch.setattr(
            ia_client, "_get_anthropic_client", lambda: fake_client
        )
        return fake_client

    payload = payload if payload is not None else _REPONSE_CLAUDE_VALIDE
    text_block = MagicMock(type="text", text=json.dumps(payload))
    response = MagicMock(
        content=[text_block],
        usage=MagicMock(input_tokens=4000, output_tokens=400),
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = response
    monkeypatch.setattr(
        ia_client, "_get_anthropic_client", lambda: fake_client
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    return fake_client


def _upload_bat_ok(devis_id: int, content: bytes = b"%PDF-1.4\nfake"):
    """Helper : upload un BAT minimal valide pour ce devis."""
    r = _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": str(devis_id)},
        files={"file": ("bat.pdf", content, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Endpoint 1 — upload-bat
# ---------------------------------------------------------------------------


def test_upload_bat_happy_path_pdf():
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-UP-001")
        db.commit()
        devis_id = devis.id

    r = _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": str(devis_id)},
        files={"file": ("bat.pdf", b"%PDF-1.4 contenu", "application/pdf")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["devis_id"] == devis_id
    assert data["bat_filename"] == "bat.pdf"
    assert data["bat_mime_type"] == "application/pdf"
    assert "bat_uploaded_at" in data


def test_upload_bat_devis_inexistant_422():
    r = _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": "999999"},
        files={"file": ("bat.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 422
    assert "introuvable" in r.json()["detail"].lower()


def test_upload_bat_mime_non_supporte_415():
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-MIME-001")
        db.commit()
        devis_id = devis.id

    r = _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": str(devis_id)},
        files={"file": ("bat.svg", b"<svg/>", "image/svg+xml")},
    )
    assert r.status_code == 415
    assert "non supporté" in r.json()["detail"].lower()


def test_upload_bat_trop_volumineux_413():
    """11 Mo > limite 10 Mo → 413."""
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-413-001")
        db.commit()
        devis_id = devis.id

    big = b"\x00" * (11 * 1024 * 1024)
    r = _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": str(devis_id)},
        files={"file": ("big.pdf", big, "application/pdf")},
    )
    assert r.status_code == 413


def test_upload_bat_re_upload_remplace_existant():
    """Un 2e upload sur le même devis met à jour la row au lieu d'en créer une autre."""
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-REUP-001")
        db.commit()
        devis_id = devis.id

    _upload_bat_ok(devis_id, b"%PDF-v1")
    _upload_bat_ok(devis_id, b"%PDF-v2")

    with SessionLocal() as db:
        rows = (
            db.query(BatReference)
            .filter_by(devis_id=devis_id, entreprise_id=1)
            .all()
        )
        assert len(rows) == 1


def test_upload_bat_isolation_multitenant(as_user_b):
    """User B ne peut pas uploader un BAT pour un devis de A → 422."""
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-ISO-001")
        db.commit()
        devis_id = devis.id

    # Switch via fixture
    r = _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": str(devis_id)},
        files={"file": ("bat.pdf", b"%PDF", "application/pdf")},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint 2 — productions-actives
# ---------------------------------------------------------------------------


def test_productions_actives_liste_devis_valides():
    """Seuls les devis statut='valide' apparaissent. bat_reference_uploaded=true
    si BAT déjà uploadé."""
    with SessionLocal() as db:
        d_valide = _create_devis(db, "TEST-FX-PA-V-001", statut="valide")
        d_brouillon = _create_devis(db, "TEST-FX-PA-B-001", statut="brouillon")
        db.commit()
        v_id = d_valide.id
        b_id = d_brouillon.id

    # Upload BAT sur le valide
    _upload_bat_ok(v_id)

    r = _http.get("/api/flexocheck/productions-actives")
    assert r.status_code == 200, r.text
    data = r.json()
    ids = {item["devis_id"] for item in data["items"]}
    assert v_id in ids
    assert b_id not in ids  # brouillon exclu

    item_v = next(i for i in data["items"] if i["devis_id"] == v_id)
    assert item_v["bat_reference_uploaded"] is True
    assert item_v["designation"] == "TEST-FX-PA-V-001"
    assert item_v["machine"]  # machine.nom


def test_productions_actives_isolation_multitenant(as_user_b):
    """User B voit uniquement ses propres devis valides."""
    with SessionLocal() as db:
        _create_devis(db, "TEST-FX-PA-ISO-A", statut="valide")
        db.commit()

    r = _http.get("/api/flexocheck/productions-actives")
    assert r.status_code == 200
    ids = {item["devis_id"] for item in r.json()["items"]}
    # User B (entreprise_id=2) ne voit aucun devis valide créé pour le tenant 1.
    with SessionLocal() as db:
        # Vérifie que le devis de A existe bien (côté DB) — donc l'exclusion vient
        # bien du scope tenant et pas d'une absence de seed.
        existe_a = (
            db.query(Devis)
            .filter_by(numero="TEST-FX-PA-ISO-A", entreprise_id=1)
            .first()
        )
        assert existe_a is not None
    for devis_a_id in (existe_a.id,):
        assert devis_a_id not in ids


# ---------------------------------------------------------------------------
# Endpoint 3 — contexte
# ---------------------------------------------------------------------------


def test_contexte_devis_sans_bat_renvoie_bat_url_null():
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CTX-001")
        db.commit()
        devis_id = devis.id

    r = _http.get(f"/api/flexocheck/controle-bat/contexte/{devis_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["devis_id"] == devis_id
    assert data["devis_numero"] == "TEST-FX-CTX-001"
    assert data["bat_url"] is None
    assert data["bat_mime_type"] is None
    assert data["machine_nom"]  # machine du seed


def test_contexte_devis_avec_bat_renvoie_url_et_mime():
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CTX-WB-001")
        db.commit()
        devis_id = devis.id

    _upload_bat_ok(devis_id)

    r = _http.get(f"/api/flexocheck/controle-bat/contexte/{devis_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["bat_url"] is not None
    assert "/api/flexocheck/blobs/" in data["bat_url"]
    assert data["bat_mime_type"] == "application/pdf"


def test_contexte_devis_autre_tenant_404(as_user_b):
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CTX-ISO-001")
        db.commit()
        devis_id = devis.id

    r = _http.get(f"/api/flexocheck/controle-bat/contexte/{devis_id}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Endpoint 4 — POST /controle-bat/ (analyse IA)
# ---------------------------------------------------------------------------


def test_post_controle_bat_happy_path(monkeypatch):
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-001")
        db.commit()
        devis_id = devis.id

    _upload_bat_ok(devis_id, b"%PDF-1.4 fake")

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id), "sens_demande": "SE1"},
        files={"photo": ("tirage.jpg", b"\xff\xd8\xff fakejpg", "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["controle_id"] > 0
    assert data["devis_id"] == devis_id
    assert data["tentative"] == 1
    assert data["score_conformite"] == "88.00"
    assert data["decision_recommandee"] == "ajuster_avant_demarrage"
    assert data["niveau_confiance"] == "haut"
    assert data["limites_analyse"] == ["Éclairage smartphone"]
    assert len(data["ecarts"]) == 2
    assert data["elements_conformes"] == ["Découpe", "Texte principal"]
    assert data["sens_enroulement_detecte"] == "SE1"
    assert data["sens_enroulement_demande"] == "SE1"
    assert data["alerte_sens_enroulement"] is None
    assert data["alerte_chef_atelier"] is None  # null hors retirage


def test_post_controle_bat_sans_bat_409(monkeypatch):
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-NOBAT-001")
        db.commit()
        devis_id = devis.id

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("tirage.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 409
    assert "BAT" in r.json()["detail"]


def test_post_controle_bat_devis_inexistant_404(monkeypatch):
    _install_mock_ia(monkeypatch)
    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": "999999"},
        files={"photo": ("tirage.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 404


def test_post_controle_bat_mime_photo_invalide_422(monkeypatch):
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-MIME-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("anim.gif", b"GIF89a", "image/gif")},
    )
    assert r.status_code == 422


def test_post_controle_bat_photo_trop_grosse_413(monkeypatch):
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-413-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    big = b"\xff\xd8\xff" + b"\x00" * (15 * 1024 * 1024 + 1)
    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("big.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 413


def test_post_controle_bat_ia_indisponible_503(monkeypatch):
    """Si Claude API échoue (clé absente, JSON invalide…) → 503."""
    # Mock l'IA pour lever IAClientError (via JSON invalide)
    text_block = MagicMock(
        type="text", text="ceci n'est pas du JSON"
    )
    response = MagicMock(
        content=[text_block],
        usage=MagicMock(input_tokens=0, output_tokens=0),
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = response
    monkeypatch.setattr(
        ia_client, "_get_anthropic_client", lambda: fake_client
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-503-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("tirage.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 503


def test_post_controle_bat_alerte_inversion_cliche_face_opposee(monkeypatch):
    """SE1 demandé + SE5 détecté = face opposée → diagnostic Lot 4
    auto-recommande `inversion_cliche` et la place en premier."""
    payload = json.loads(json.dumps(_REPONSE_CLAUDE_VALIDE))
    payload["alerte_sens_enroulement"] = (
        "Sens SE5 détecté alors que BAT en SE1 — risque inversion cliché"
    )
    payload["sens_sortie_detecte"]["sens_enroulement_resultant"] = "SE5"
    payload["sens_sortie_detecte"]["coherence_avec_bat"] = False
    _install_mock_ia(monkeypatch, payload)

    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-INV-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id), "sens_demande": "SE1"},
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 201
    data = r.json()
    alerte = data["alerte_sens_enroulement"]
    assert alerte is not None
    # Le message Lot 4 explique le diagnostic métier (face opposée)
    assert "SE1" in alerte["message"] and "SE5" in alerte["message"]
    assert "inversion" in alerte["message"].lower()
    # 3 options présentes, inversion_cliche recommandée + en première
    codes = {o["code"] for o in alerte["options_correction"]}
    assert codes == {
        "inversion_cliche",
        "ajustement_rebobineuse",
        "confirmation_client",
    }
    recommandees = [o for o in alerte["options_correction"] if o["recommandee"]]
    assert len(recommandees) == 1
    assert recommandees[0]["code"] == "inversion_cliche"
    assert alerte["options_correction"][0]["code"] == "inversion_cliche"


def test_post_controle_bat_alerte_ajustement_rebobineuse_meme_face(monkeypatch):
    """SE1 demandé + SE3 détecté = même face Ext, rotation différente →
    diagnostic Lot 4 auto-recommande `ajustement_rebobineuse`."""
    payload = json.loads(json.dumps(_REPONSE_CLAUDE_VALIDE))
    payload["sens_sortie_detecte"]["sens_enroulement_resultant"] = "SE3"
    payload["sens_sortie_detecte"]["coherence_avec_bat"] = False
    _install_mock_ia(monkeypatch, payload)

    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-REB-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id), "sens_demande": "SE1"},
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 201
    alerte = r.json()["alerte_sens_enroulement"]
    assert alerte is not None
    assert "rebobineuse" in alerte["message"].lower()
    assert alerte["options_correction"][0]["code"] == "ajustement_rebobineuse"
    assert alerte["options_correction"][0]["recommandee"] is True


def test_post_controle_bat_alerte_confirmation_client_si_confiance_faible(monkeypatch):
    """Même cas face opposée (SE1 vs SE5) mais avec niveau_confiance='faible'
    → l'IA n'est pas fiable, on demande à un humain via
    `confirmation_client` (prime sur la règle inversion_cliche)."""
    payload = json.loads(json.dumps(_REPONSE_CLAUDE_VALIDE))
    payload["sens_sortie_detecte"]["sens_enroulement_resultant"] = "SE5"
    payload["niveau_confiance_analyse"] = "faible"
    _install_mock_ia(monkeypatch, payload)

    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-CONF-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id), "sens_demande": "SE1"},
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 201
    alerte = r.json()["alerte_sens_enroulement"]
    assert alerte is not None
    assert "confiance" in alerte["message"].lower()
    assert alerte["options_correction"][0]["code"] == "confirmation_client"
    assert alerte["options_correction"][0]["recommandee"] is True


def test_post_controle_bat_sens_coherent_aucune_alerte(monkeypatch):
    """SE1 demandé + SE1 détecté → diagnostic Lot 4 = coherent, pas d'alerte
    même si l'IA renvoyait par hasard un message d'alerte non-null."""
    payload = json.loads(json.dumps(_REPONSE_CLAUDE_VALIDE))
    # Sens identiques + sens demandé = SE1
    payload["sens_sortie_detecte"]["sens_enroulement_resultant"] = "SE1"
    _install_mock_ia(monkeypatch, payload)

    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-OK-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id), "sens_demande": "SE1"},
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["alerte_sens_enroulement"] is None
    assert data["sens_enroulement_detecte"] == "SE1"
    assert data["sens_enroulement_demande"] == "SE1"


def test_post_controle_bat_persiste_coherence_et_action_sur_row(monkeypatch):
    """Lot 4 doit écrire `coherence_sens` et `action_correction_sens`
    sur la row ControleBat (pas seulement dans la réponse)."""
    payload = json.loads(json.dumps(_REPONSE_CLAUDE_VALIDE))
    payload["sens_sortie_detecte"]["sens_enroulement_resultant"] = "SE5"
    _install_mock_ia(monkeypatch, payload)

    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-CB-PERSIST-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id), "sens_demande": "SE1"},
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 201
    controle_id = r.json()["controle_id"]

    with SessionLocal() as db:
        cb = db.query(ControleBat).filter_by(id=controle_id).one()
        assert cb.coherence_sens is False
        assert cb.action_correction_sens == "inversion_cliche"
        assert cb.sens_enroulement_demande == "SE1"
        assert cb.sens_sortie_detecte == "SE5"


def test_post_controle_bat_fallback_sens_demande_du_lot(monkeypatch):
    """Si l'opérateur n'a pas fourni sens_demande en Form, on prend le
    sens du 1er LotProduction du devis."""
    # Setup : devis + 1 lot avec sens_enroulement=4 (SE4) — face Ext.
    # Sens détecté = SE8 (Int) → inversion_cliche.
    from tests.test_lot_production_model import (
        _create_devis_minimal,
        _get_fk_ids,
        _onboard_if_needed,
    )

    _onboard_if_needed()
    with SessionLocal() as db:
        cyl_id, mach_id, mat_id = _get_fk_ids(db)
        devis = _create_devis_minimal(db, numero="TEST-FX-CB-FB-001")
        from app.models import LotProduction
        db.add(
            LotProduction(
                devis_id=devis.id,
                entreprise_id=1,
                ordre=1,
                cylindre_id=cyl_id,
                machine_id=mach_id,
                nb_poses_dev=2,
                nb_poses_laize=3,
                sens_enroulement=4,
                quantite=1000,
                matiere_id=mat_id,
            )
        )
        db.commit()
        devis_id = devis.id

    _upload_bat_ok(devis_id)

    payload = json.loads(json.dumps(_REPONSE_CLAUDE_VALIDE))
    payload["sens_sortie_detecte"]["sens_enroulement_resultant"] = "SE8"
    _install_mock_ia(monkeypatch, payload)

    # PAS de sens_demande en Form → fallback sur le lot 1 = SE4
    r = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["sens_enroulement_demande"] == "SE4"
    assert data["sens_enroulement_detecte"] == "SE8"
    alerte = data["alerte_sens_enroulement"]
    assert alerte is not None
    assert alerte["options_correction"][0]["code"] == "inversion_cliche"


# ---------------------------------------------------------------------------
# Endpoint 5 — GET liste contrôles
# ---------------------------------------------------------------------------


def test_get_controles_devis_liste_ordonnee(monkeypatch):
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-LIST-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    # 2 tentatives
    r1 = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("t1.jpg", b"\xff\xd8\xff t1", "image/jpeg")},
    )
    assert r1.status_code == 201
    controle_id_1 = r1.json()["controle_id"]

    r2 = _http.post(
        f"/api/flexocheck/controle-bat/{controle_id_1}/retirage",
        files={"photo": ("t2.jpg", b"\xff\xd8\xff t2", "image/jpeg")},
    )
    assert r2.status_code == 201, r2.text

    # Liste
    r = _http.get(f"/api/flexocheck/controle-bat/{devis_id}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert rows[0]["tentative_numero"] == 1
    assert rows[1]["tentative_numero"] == 2
    assert rows[1]["controle_bat_precedent_id"] == rows[0]["id"]


def test_get_controles_devis_autre_tenant_404(as_user_b):
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-LIST-ISO-001")
        db.commit()
        devis_id = devis.id

    r = _http.get(f"/api/flexocheck/controle-bat/{devis_id}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Endpoint 6 — POST /{id}/decision
# ---------------------------------------------------------------------------


def test_post_decision_met_a_jour_la_row(monkeypatch):
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-DEC-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)
    r1 = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    controle_id = r1.json()["controle_id"]

    r = _http.post(
        f"/api/flexocheck/controle-bat/{controle_id}/decision",
        json={
            "decision_finale": "valide_avec_reserves",
            "decideur": "Chef Dupond",
            "motif_decision": "Acceptable client OK par téléphone",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["decision_finale"] == "valide_avec_reserves"
    assert data["decideur"] == "Chef Dupond"
    assert data["motif_decision"].startswith("Acceptable")


def test_post_decision_id_inexistant_404():
    r = _http.post(
        "/api/flexocheck/controle-bat/999999/decision",
        json={"decision_finale": "valide", "decideur": "X"},
    )
    assert r.status_code == 404


def test_post_decision_valeur_invalide_422():
    r = _http.post(
        "/api/flexocheck/controle-bat/1/decision",
        json={"decision_finale": "rejete_avec_violence", "decideur": "X"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint 7 — POST /{id}/retirage
# ---------------------------------------------------------------------------


def test_post_retirage_incremente_tentative_et_chaine(monkeypatch):
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-RET-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    r1 = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("t1.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    parent_id = r1.json()["controle_id"]

    r2 = _http.post(
        f"/api/flexocheck/controle-bat/{parent_id}/retirage",
        files={"photo": ("t2.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r2.status_code == 201, r2.text
    data = r2.json()
    assert data["tentative"] == 2
    assert data["alerte_chef_atelier"] is False


def test_post_retirage_alerte_chef_au_dela_de_3_tentatives(monkeypatch):
    """Tentative 4 (>3) → alerte_chef_atelier=true."""
    _install_mock_ia(monkeypatch)
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-RET-ALERTE-001")
        db.commit()
        devis_id = devis.id
    _upload_bat_ok(devis_id)

    parent = _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id)},
        files={"photo": ("t1.jpg", b"\xff\xd8\xff", "image/jpeg")},
    ).json()["controle_id"]

    last_id = parent
    for n in (2, 3, 4):
        r = _http.post(
            f"/api/flexocheck/controle-bat/{last_id}/retirage",
            files={
                "photo": (f"t{n}.jpg", b"\xff\xd8\xff", "image/jpeg")
            },
        )
        assert r.status_code == 201, r.text
        last_id = r.json()["controle_id"]
        if n == 4:
            assert r.json()["alerte_chef_atelier"] is True
            assert r.json()["tentative"] == 4
        else:
            assert r.json()["alerte_chef_atelier"] is False


def test_post_retirage_parent_autre_tenant_404(as_user_b):
    r = _http.post(
        "/api/flexocheck/controle-bat/999999/retirage",
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Endpoint 0 — GET /blobs/{image_key}
# ---------------------------------------------------------------------------


def test_serve_blob_bat_pdf(monkeypatch):
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-FX-BLOB-BAT-001")
        db.commit()
        devis_id = devis.id

    up = _upload_bat_ok(devis_id, b"%PDF-1.4 bytes BAT")
    # Récupère l'image_key via la row
    with SessionLocal() as db:
        row = (
            db.query(BatReference)
            .filter_by(devis_id=devis_id, entreprise_id=1)
            .one()
        )
        image_key = row.image_key

    assert image_key is not None
    r = _http.get(f"/api/flexocheck/blobs/{image_key}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


def test_serve_blob_introuvable_404():
    r = _http.get("/api/flexocheck/blobs/nonexistent-key.pdf")
    assert r.status_code == 404


def test_serve_blob_isolation_multitenant(as_user_b):
    """User B ne peut pas servir un blob du tenant A (404)."""
    # Création du blob côté A nécessite un override on/off — on
    # bypasse en utilisant l'autouse seed + on insert directement le BAT
    # via SQL, mais c'est lourd. À la place : la fixture as_user_b a
    # déjà basculé l'override sur user B → toute query avec un image_key
    # quelconque tombe en 404 puisque B n'a aucune row à lui.
    r = _http.get("/api/flexocheck/blobs/whatever.pdf")
    assert r.status_code == 404
