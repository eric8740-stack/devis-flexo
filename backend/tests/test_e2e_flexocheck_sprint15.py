"""Tests E2E FlexoCheck — Sprint 15 Lot 5.

Pipeline opérateur complet enchaîné dans un même test (différence avec
les tests router Lot 3-4 qui vérifient chaque endpoint en isolation) :

  upload BAT
    → GET contexte
    → POST controle-bat (analyse IA mockée)
    → GET liste (1 tentative)
    → POST decision

Avec variantes :
  - re-tirages successifs jusqu'à dépasser le seuil chef d'atelier (>3)
  - isolation multi-tenant sur toute la chaîne
  - productions-actives évolue avec `bat_reference_uploaded`

Claude API toujours mockée — 0 appel réel. Pour les pipelines à
plusieurs analyses, on utilise `side_effect=[...]` sur le mock pour
servir des réponses successives.
"""
import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import BatReference, ControleBat, Devis
from app.services.ia import client as ia_client


_http = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_devis(
    db, numero: str = "TEST-E2E-001", statut: str = "valide"
) -> Devis:
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


def _claude_response(payload: dict, input_tokens: int = 4000, output_tokens: int = 400):
    text_block = MagicMock(type="text", text=json.dumps(payload))
    return MagicMock(
        content=[text_block],
        usage=MagicMock(
            input_tokens=input_tokens, output_tokens=output_tokens
        ),
    )


def _install_mock_responses(monkeypatch, payloads: list[dict]):
    """Installe un mock qui sert `payloads` successivement (side_effect)."""
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _claude_response(p) for p in payloads
    ]
    monkeypatch.setattr(
        ia_client, "_get_anthropic_client", lambda: fake_client
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    return fake_client


# Réponse IA "ajuster avant démarrage" — utilisée pour la majorité des
# scenarii car simule une production en cours d'optim. Pas d'écart sens.
def _reponse_ajuster(score: int = 75) -> dict:
    return {
        "score_conformite_global": score,
        "decision_recommandee": "ajuster_avant_demarrage",
        "ecarts_detectes": [
            {
                "type": "couleur",
                "gravite": "majeur",
                "localisation": "logo",
                "description": "Couleur dérive",
                "suggestion_correction": "Ajuster station 1",
            }
        ],
        "elements_conformes": ["Découpe", "Texte"],
        "elements_manquants": [],
        "niveau_confiance_analyse": "haut",
        "limites_analyse": [],
        "sens_sortie_detecte": {
            "orientation_etiquette": "tête en haut",
            "sens_lecture": "gauche-vers-droite",
            "sens_enroulement_resultant": "SE1",
            "coherence_avec_bat": True,
        },
        "alerte_sens_enroulement": None,
    }


def _reponse_valider(score: int = 95) -> dict:
    return {
        "score_conformite_global": score,
        "decision_recommandee": "valider",
        "ecarts_detectes": [],
        "elements_conformes": ["Tout"],
        "elements_manquants": [],
        "niveau_confiance_analyse": "haut",
        "limites_analyse": [],
        "sens_sortie_detecte": {
            "orientation_etiquette": "tête en haut",
            "sens_lecture": "gauche-vers-droite",
            "sens_enroulement_resultant": "SE1",
            "coherence_avec_bat": True,
        },
        "alerte_sens_enroulement": None,
    }


def _upload_bat(devis_id: int):
    r = _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": str(devis_id)},
        files={"file": ("bat.pdf", b"%PDF-1.4 BAT", "application/pdf")},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _post_controle(devis_id: int, sens_demande: str = "SE1"):
    return _http.post(
        "/api/flexocheck/controle-bat/",
        data={"devis_id": str(devis_id), "sens_demande": sens_demande},
        files={"photo": ("t.jpg", b"\xff\xd8\xff jpg", "image/jpeg")},
    )


def _post_retirage(controle_id: int, sens_demande: str = "SE1"):
    return _http.post(
        f"/api/flexocheck/controle-bat/{controle_id}/retirage",
        data={"sens_demande": sens_demande},
        files={"photo": ("t.jpg", b"\xff\xd8\xff jpg", "image/jpeg")},
    )


# ---------------------------------------------------------------------------
# 1) Pipeline complet "happy path" : upload → contrôle → decision
# ---------------------------------------------------------------------------


def test_e2e_pipeline_complet_happy_path(monkeypatch):
    """L'opérateur upload le BAT, fait UN contrôle qui passe vert, et
    enregistre la décision finale. Vérifie la cohérence de chaque
    étape + la persistance finale en DB."""
    _install_mock_responses(monkeypatch, [_reponse_valider()])

    # Étape 0 — création du devis valide
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-E2E-HP-001")
        db.commit()
        devis_id = devis.id

    # Étape 1 — upload BAT
    bat = _upload_bat(devis_id)
    assert bat["bat_filename"] == "bat.pdf"
    assert bat["bat_mime_type"] == "application/pdf"

    # Étape 2 — GET contexte : le BAT est attaché
    r_ctx = _http.get(
        f"/api/flexocheck/controle-bat/contexte/{devis_id}"
    )
    assert r_ctx.status_code == 200
    ctx = r_ctx.json()
    assert ctx["bat_url"] is not None
    assert ctx["bat_mime_type"] == "application/pdf"
    assert ctx["devis_numero"] == "TEST-E2E-HP-001"

    # Étape 3 — POST contrôle + analyse IA mockée
    r_ctrl = _post_controle(devis_id)
    assert r_ctrl.status_code == 201, r_ctrl.text
    ctrl = r_ctrl.json()
    assert ctrl["tentative"] == 1
    assert ctrl["decision_recommandee"] == "valider"
    assert ctrl["alerte_sens_enroulement"] is None
    assert ctrl["alerte_chef_atelier"] is None  # pas un retirage
    controle_id = ctrl["controle_id"]

    # Étape 4 — GET liste : 1 tentative ordonnée, decision_finale=en_attente
    r_list = _http.get(f"/api/flexocheck/controle-bat/{devis_id}")
    assert r_list.status_code == 200
    rows = r_list.json()
    assert len(rows) == 1
    assert rows[0]["id"] == controle_id
    assert rows[0]["tentative_numero"] == 1
    assert rows[0]["decision_finale"] == "en_attente"

    # Étape 5 — POST decision finale
    r_dec = _http.post(
        f"/api/flexocheck/controle-bat/{controle_id}/decision",
        json={
            "decision_finale": "valide",
            "decideur": "Chef Atelier Martin",
            "motif_decision": "Score 95, aucun écart",
        },
    )
    assert r_dec.status_code == 200
    assert r_dec.json()["decision_finale"] == "valide"

    # Vérification DB : la row finale est cohérente
    with SessionLocal() as db:
        cb = db.query(ControleBat).filter_by(id=controle_id).one()
        assert cb.decision_finale == "valide"
        assert cb.decideur == "Chef Atelier Martin"
        assert cb.tentative_numero == 1
        assert cb.controle_bat_precedent_id is None
        assert float(cb.score_conformite) == 95.0


# ---------------------------------------------------------------------------
# 2) Pipeline retirages successifs : alerte chef atelier après 3 tentatives
# ---------------------------------------------------------------------------


def test_e2e_chaine_retirages_et_alerte_chef_atelier(monkeypatch):
    """4 tentatives successives : la 4e (tentative > 3) déclenche
    `alerte_chef_atelier=true`. Vérifie aussi le chaînage
    `controle_bat_precedent_id` sur toute la chaîne."""
    # 4 appels Claude attendus
    _install_mock_responses(
        monkeypatch,
        [
            _reponse_ajuster(score=60),  # tentative 1
            _reponse_ajuster(score=70),  # tentative 2
            _reponse_ajuster(score=78),  # tentative 3
            _reponse_ajuster(score=85),  # tentative 4
        ],
    )

    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-E2E-CHAINE-001")
        db.commit()
        devis_id = devis.id
    _upload_bat(devis_id)

    # Tentative 1 — contrôle initial
    r1 = _post_controle(devis_id)
    assert r1.status_code == 201
    t1 = r1.json()
    assert t1["tentative"] == 1
    assert t1["alerte_chef_atelier"] is None  # contrôle initial

    # Tentatives 2-4 — retirages
    last_id = t1["controle_id"]
    expected_alertes = [False, False, True]  # 2, 3 = OK ; 4 > 3 → alerte
    expected_scores = [70, 78, 85]
    for idx, (alerte_attendue, score_attendu) in enumerate(
        zip(expected_alertes, expected_scores), start=2
    ):
        r = _post_retirage(last_id)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["tentative"] == idx, (
            f"tentative {idx} attendue, reçue {data['tentative']}"
        )
        assert data["alerte_chef_atelier"] is alerte_attendue, (
            f"alerte_chef_atelier tentative {idx} = "
            f"{data['alerte_chef_atelier']}, attendu {alerte_attendue}"
        )
        assert float(data["score_conformite"]) == score_attendu
        last_id = data["controle_id"]

    # GET liste : 4 tentatives ordonnées ASC
    r_list = _http.get(f"/api/flexocheck/controle-bat/{devis_id}")
    rows = r_list.json()
    assert len(rows) == 4
    assert [r["tentative_numero"] for r in rows] == [1, 2, 3, 4]

    # Chaîne : tentative_N.controle_bat_precedent_id = tentative_(N-1).id
    for i in range(1, 4):
        assert rows[i]["controle_bat_precedent_id"] == rows[i - 1]["id"]
    assert rows[0]["controle_bat_precedent_id"] is None  # racine


def test_e2e_retirage_decision_valide_apres_3_tentatives(monkeypatch):
    """Pipeline avec decision finale = `valide_avec_reserves` sur la
    3e tentative quand le chef d'atelier décide d'accepter le tirage."""
    _install_mock_responses(
        monkeypatch,
        [_reponse_ajuster(60), _reponse_ajuster(78), _reponse_valider(92)],
    )
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-E2E-DEC-001")
        db.commit()
        devis_id = devis.id
    _upload_bat(devis_id)

    t1 = _post_controle(devis_id).json()
    t2 = _post_retirage(t1["controle_id"]).json()
    t3 = _post_retirage(t2["controle_id"]).json()

    assert t3["tentative"] == 3
    assert t3["decision_recommandee"] == "valider"

    # Décision finale sur la dernière tentative
    r = _http.post(
        f"/api/flexocheck/controle-bat/{t3['controle_id']}/decision",
        json={
            "decision_finale": "valide_avec_reserves",
            "decideur": "Chef Dupont",
            "motif_decision": "Acceptable client OK par téléphone",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision_finale"] == "valide_avec_reserves"

    # Les 2 tentatives précédentes restent en_attente
    with SessionLocal() as db:
        cb1 = db.query(ControleBat).filter_by(id=t1["controle_id"]).one()
        cb2 = db.query(ControleBat).filter_by(id=t2["controle_id"]).one()
        assert cb1.decision_finale == "en_attente"
        assert cb2.decision_finale == "en_attente"


# ---------------------------------------------------------------------------
# 3) Isolation multi-tenant sur toute la chaîne
# ---------------------------------------------------------------------------


def test_e2e_isolation_tenant_b_voit_pas_les_donnees_de_a(
    monkeypatch, switch_to_user_b
):
    """User A crée une chaîne complète (BAT + contrôle). User B (autre
    tenant) tente chaque endpoint sur les mêmes IDs → 404/422 partout."""
    _install_mock_responses(monkeypatch, [_reponse_valider()])

    # User A (admin demo, override autouse) — pipeline complet
    with SessionLocal() as db:
        devis = _create_devis(db, "TEST-E2E-ISO-001")
        db.commit()
        devis_id_a = devis.id

    _upload_bat(devis_id_a)
    r_ctrl = _post_controle(devis_id_a)
    controle_id_a = r_ctrl.json()["controle_id"]

    # Snapshot DB côté A — on vérifie que la row existe bien avant le switch
    with SessionLocal() as db:
        assert db.query(BatReference).filter_by(devis_id=devis_id_a).first()
        assert db.query(ControleBat).filter_by(id=controle_id_a).first()

    # Switch vers user B (entreprise_id=2)
    switch_to_user_b()

    # Tous les endpoints scopés → 404/422 (anti-énumération)
    assert _http.get(
        f"/api/flexocheck/controle-bat/contexte/{devis_id_a}"
    ).status_code == 404
    assert _http.get(
        f"/api/flexocheck/controle-bat/{devis_id_a}"
    ).status_code == 404
    assert _http.post(
        f"/api/flexocheck/controle-bat/{controle_id_a}/decision",
        json={"decision_finale": "valide", "decideur": "B"},
    ).status_code == 404
    assert _http.post(
        f"/api/flexocheck/controle-bat/{controle_id_a}/retirage",
        files={"photo": ("t.jpg", b"\xff\xd8\xff", "image/jpeg")},
    ).status_code == 404

    # Upload BAT sur un devis hors scope → 422 (validation devis_id)
    assert _http.post(
        "/api/flexocheck/controle-bat/upload-bat",
        data={"devis_id": str(devis_id_a)},
        files={"file": ("bat.pdf", b"%PDF", "application/pdf")},
    ).status_code == 422

    # B ne voit pas le devis de A dans productions-actives
    r_prod = _http.get("/api/flexocheck/productions-actives")
    assert r_prod.status_code == 200
    ids_b = {item["devis_id"] for item in r_prod.json()["items"]}
    assert devis_id_a not in ids_b


# ---------------------------------------------------------------------------
# 4) productions-actives évolue avec bat_reference_uploaded
# ---------------------------------------------------------------------------


def test_e2e_productions_actives_evolue_apres_upload_bat():
    """Avant upload : bat_reference_uploaded=false ; après : true.
    Vérifie qu'un 2e devis valide reste en bat_reference_uploaded=false."""
    with SessionLocal() as db:
        d1 = _create_devis(db, "TEST-E2E-PA1-001", statut="valide")
        d2 = _create_devis(db, "TEST-E2E-PA2-001", statut="valide")
        db.commit()
        d1_id, d2_id = d1.id, d2.id

    # T0 — aucun BAT uploadé
    r0 = _http.get("/api/flexocheck/productions-actives")
    assert r0.status_code == 200
    items_par_id = {it["devis_id"]: it for it in r0.json()["items"]}
    assert items_par_id[d1_id]["bat_reference_uploaded"] is False
    assert items_par_id[d2_id]["bat_reference_uploaded"] is False

    # T1 — upload BAT sur d1
    _upload_bat(d1_id)

    r1 = _http.get("/api/flexocheck/productions-actives")
    items_par_id = {it["devis_id"]: it for it in r1.json()["items"]}
    assert items_par_id[d1_id]["bat_reference_uploaded"] is True
    assert items_par_id[d2_id]["bat_reference_uploaded"] is False
