"""Tests endpoints historique des analyses photo — feat-historique-analyses.

Couvre les 4 endpoints (list, get, delete, serve_photo) avec emphase
sur l'isolation multi-tenant :
  - GET /api/ia/analyses : liste paginée scopée user.entreprise_id
  - GET /api/ia/analyses/{id} : 404 si autre tenant (pas 403)
  - DELETE /api/ia/analyses/{id} : hard delete row + fichier
  - GET /api/ia/photos/{key} : FileResponse, 404 si autre tenant ou
    fichier absent

Aucun appel reel Claude (l'endpoint POST n'est pas testé ici, deja
couvert par test_ia_router.py). On insère directement les rows.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models import AnalysePhotoEtiquette
from app.services.ia import photo_storage


client = TestClient(app)


@pytest.fixture
def cleanup_analyses(tmp_path, monkeypatch):
    """Purge les rows AnalysePhotoEtiquette pour les tenants test +
    isole le PHOTO_UPLOAD_DIR sur tmp_path."""
    monkeypatch.setenv("PHOTO_UPLOAD_DIR", str(tmp_path / "photos"))
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


def _create_analyse(
    db: Session,
    entreprise_id: int,
    *,
    image_filename: str = "test.jpg",
    image_key: str | None = None,
    photo_mime_type: str = "image/jpeg",
    resultats: dict | None = None,
) -> AnalysePhotoEtiquette:
    """Helper : crée une row analyse en BDD, avec image_key unique
    par défaut."""
    import uuid as _uuid

    key = image_key or f"{_uuid.uuid4().hex}.jpg"
    row = AnalysePhotoEtiquette(
        entreprise_id=entreprise_id,
        photo_mime_type=photo_mime_type,
        image_filename=image_filename,
        image_key=key,
        image_size_bytes=100,
        resultats_ia=resultats or {"niveau_confiance": "moyen"},
        niveau_confiance="moyen",
        nombre_couleurs_distinctes=4,
        model_utilise="claude-sonnet-4-6",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# GET /api/ia/analyses (liste paginée)
# ---------------------------------------------------------------------------


def test_list_analyses_vide_par_defaut(cleanup_analyses):
    r = client.get("/api/ia/analyses")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {"items": [], "page": 1, "limit": 20, "total": 0}


def test_list_analyses_retourne_ses_propres_analyses(cleanup_analyses):
    db = SessionLocal()
    try:
        _create_analyse(db, entreprise_id=1, image_filename="a1.jpg")
        _create_analyse(db, entreprise_id=1, image_filename="a2.jpg")
        _create_analyse(db, entreprise_id=1, image_filename="a3.jpg")
    finally:
        db.close()

    r = client.get("/api/ia/analyses")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    filenames = [i["image_filename"] for i in body["items"]]
    assert set(filenames) == {"a1.jpg", "a2.jpg", "a3.jpg"}


def test_list_analyses_filtre_par_tenant(cleanup_analyses, switch_to_user_b):
    """User A crée 3 analyses, user B en crée 2. User B → 2 items, jamais
    ceux de A."""
    # Pre-switch pour s'assurer que l'entreprise B existe (FK).
    # Ça pose aussi l'override get_current_user sur B — on insère les
    # rows directement en DB (bypass API) puis on bascule l'override
    # final selon le user testé.
    switch_to_user_b()

    db = SessionLocal()
    try:
        for i in range(3):
            _create_analyse(
                db, entreprise_id=1, image_filename=f"a-{i}.jpg"
            )
        for i in range(2):
            _create_analyse(
                db, entreprise_id=2, image_filename=f"b-{i}.jpg"
            )
    finally:
        db.close()

    # Actuellement on est sous l'identité B (suite à switch_to_user_b()).
    r = client.get("/api/ia/analyses")
    body = r.json()
    assert body["total"] == 2
    filenames = [i["image_filename"] for i in body["items"]]
    assert all(f.startswith("b-") for f in filenames)


def test_list_analyses_pagination(cleanup_analyses):
    db = SessionLocal()
    try:
        for i in range(25):
            _create_analyse(
                db, entreprise_id=1, image_filename=f"item-{i:02d}.jpg"
            )
    finally:
        db.close()

    r1 = client.get("/api/ia/analyses?page=1&limit=20").json()
    assert r1["total"] == 25
    assert len(r1["items"]) == 20

    r2 = client.get("/api/ia/analyses?page=2&limit=20").json()
    assert len(r2["items"]) == 5

    # Pas de chevauchement entre pages
    ids_p1 = {i["id"] for i in r1["items"]}
    ids_p2 = {i["id"] for i in r2["items"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_list_analyses_tri_created_at_desc(cleanup_analyses):
    """Le plus récent en tête. Tie-break par id desc côté router."""
    db = SessionLocal()
    try:
        # Insertion séquentielle → ids strictement croissants. Si
        # created_at sont identiques (timestamp ms), le tie-break id desc
        # du router doit faire ressortir le dernier insert en tête.
        first = _create_analyse(db, entreprise_id=1, image_filename="old.jpg")
        last = _create_analyse(db, entreprise_id=1, image_filename="new.jpg")
        first_id = first.id
        last_id = last.id
    finally:
        db.close()

    r = client.get("/api/ia/analyses").json()
    assert r["items"][0]["id"] == last_id
    assert r["items"][-1]["id"] == first_id


def test_list_analyses_limit_borné_à_100(cleanup_analyses):
    """`?limit=10000` doit retomber sur 20 (borne anti-DOS)."""
    r = client.get("/api/ia/analyses?limit=10000")
    assert r.json()["limit"] == 20


def test_list_analyses_page_zero_devient_un(cleanup_analyses):
    r = client.get("/api/ia/analyses?page=0")
    assert r.json()["page"] == 1


def test_list_analyses_403_si_pas_flexocheck(
    cleanup_analyses, as_user_flexocompare_only
):
    r = client.get("/api/ia/analyses")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/ia/analyses/{id} (détail)
# ---------------------------------------------------------------------------


def test_get_analyse_detail_happy_path(cleanup_analyses):
    db = SessionLocal()
    try:
        row = _create_analyse(
            db,
            entreprise_id=1,
            image_filename="detail.jpg",
            resultats={"niveau_confiance": "haut", "matiere_estimee": {"type": "papier"}},
        )
    finally:
        db.close()

    r = client.get(f"/api/ia/analyses/{row.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == row.id
    assert body["image_filename"] == "detail.jpg"
    assert body["resultats_ia"]["niveau_confiance"] == "haut"
    assert body["resultats_ia"]["matiere_estimee"]["type"] == "papier"


def test_get_analyse_autre_tenant_retourne_404(
    cleanup_analyses, switch_to_user_b
):
    """User B demande une analyse de A → 404 (pas 403, ne pas leak)."""
    db = SessionLocal()
    try:
        row_a = _create_analyse(db, entreprise_id=1, image_filename="a.jpg")
    finally:
        db.close()

    switch_to_user_b()
    r = client.get(f"/api/ia/analyses/{row_a.id}")
    assert r.status_code == 404


def test_get_analyse_inexistante_404(cleanup_analyses):
    r = client.get("/api/ia/analyses/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/ia/analyses/{id}
# ---------------------------------------------------------------------------


def test_delete_analyse_supprime_row_et_fichier(cleanup_analyses, tmp_path):
    """Hard delete row + fichier disque associé."""
    db = SessionLocal()
    try:
        # On sauve un vrai fichier dans tmp puis on associe l'image_key
        key, _ = photo_storage.save_photo(b"fake-jpeg-bytes", "image/jpeg")
        assert key is not None
        path = photo_storage.get_photo_path(key)
        assert path is not None and path.exists()

        row = _create_analyse(db, entreprise_id=1, image_key=key)
    finally:
        db.close()

    r = client.delete(f"/api/ia/analyses/{row.id}")
    assert r.status_code == 204

    # Row DB supprimée
    db = SessionLocal()
    try:
        assert (
            db.query(AnalysePhotoEtiquette).filter_by(id=row.id).first()
            is None
        )
    finally:
        db.close()

    # Fichier disque supprimé
    assert photo_storage.get_photo_path(key) is None


def test_delete_analyse_autre_tenant_404(cleanup_analyses, switch_to_user_b):
    db = SessionLocal()
    try:
        row_a = _create_analyse(db, entreprise_id=1)
    finally:
        db.close()

    switch_to_user_b()
    r = client.delete(f"/api/ia/analyses/{row_a.id}")
    assert r.status_code == 404

    # Sanity : la row A n'a PAS été supprimée par le call de B
    db = SessionLocal()
    try:
        assert (
            db.query(AnalysePhotoEtiquette).filter_by(id=row_a.id).first()
            is not None
        )
    finally:
        db.close()


def test_delete_analyse_inexistante_404(cleanup_analyses):
    r = client.delete("/api/ia/analyses/999999")
    assert r.status_code == 404


def test_delete_analyse_sans_image_key_ok(cleanup_analyses):
    """Analyse sans photo physique (mode degrade ou ancienne row) →
    delete row OK, pas d'erreur sur le cleanup fichier."""
    db = SessionLocal()
    try:
        row = AnalysePhotoEtiquette(
            entreprise_id=1,
            resultats_ia={},
            image_key=None,  # explicite
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        row_id = row.id
    finally:
        db.close()

    r = client.delete(f"/api/ia/analyses/{row_id}")
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# GET /api/ia/photos/{key} (serve_photo)
# ---------------------------------------------------------------------------


def test_serve_photo_happy_path(cleanup_analyses):
    db = SessionLocal()
    try:
        key, _ = photo_storage.save_photo(b"\x89PNGfake", "image/png")
        assert key is not None
        _create_analyse(
            db, entreprise_id=1, image_key=key, photo_mime_type="image/png"
        )
    finally:
        db.close()

    r = client.get(f"/api/ia/photos/{key}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert r.content == b"\x89PNGfake"


def test_serve_photo_autre_tenant_404(cleanup_analyses, switch_to_user_b):
    db = SessionLocal()
    try:
        key, _ = photo_storage.save_photo(b"fake-jpeg", "image/jpeg")
        assert key is not None
        _create_analyse(db, entreprise_id=1, image_key=key)
    finally:
        db.close()

    switch_to_user_b()
    r = client.get(f"/api/ia/photos/{key}")
    assert r.status_code == 404


def test_serve_photo_key_inexistante_404(cleanup_analyses):
    r = client.get("/api/ia/photos/inexistante.jpg")
    assert r.status_code == 404


def test_serve_photo_row_existe_mais_fichier_absent_404(cleanup_analyses):
    """Row existe avec image_key mais fichier physique absent
    (mode degrade Volume non monte) → 404 cohérent."""
    db = SessionLocal()
    try:
        _create_analyse(
            db, entreprise_id=1, image_key="ghost.jpg"
        )
    finally:
        db.close()

    r = client.get("/api/ia/photos/ghost.jpg")
    assert r.status_code == 404


def test_serve_photo_403_si_pas_flexocheck(
    cleanup_analyses, as_user_flexocompare_only
):
    r = client.get("/api/ia/photos/whatever.jpg")
    assert r.status_code == 403
