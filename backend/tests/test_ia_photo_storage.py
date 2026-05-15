"""Tests photo_storage service — feat historique analyses.

Vérifie save / get_photo_path / delete avec :
  - Tmp directory pytest (pas de pollution disque)
  - Mode dégradé si répertoire non writable (Volume non monté)
  - Protection path traversal sur get_photo_path
  - Naming UUID + extension par mime
"""
from pathlib import Path

import pytest

from app.services.ia import photo_storage


@pytest.fixture(autouse=True)
def _override_upload_dir(tmp_path, monkeypatch):
    """Force PHOTO_UPLOAD_DIR sur un tmp_path pour chaque test → isolation."""
    monkeypatch.setenv("PHOTO_UPLOAD_DIR", str(tmp_path / "photos"))
    yield


# ---------------------------------------------------------------------------
# get_upload_dir
# ---------------------------------------------------------------------------


def test_get_upload_dir_lit_env_var(tmp_path, monkeypatch):
    target = tmp_path / "custom"
    monkeypatch.setenv("PHOTO_UPLOAD_DIR", str(target))
    assert photo_storage.get_upload_dir() == target


def test_get_upload_dir_default_dev_si_pas_d_env(monkeypatch):
    monkeypatch.delenv("PHOTO_UPLOAD_DIR", raising=False)
    p = photo_storage.get_upload_dir()
    # default = <repo>/backend/.uploads/photos
    assert p.name == "photos"
    assert p.parent.name == ".uploads"


# ---------------------------------------------------------------------------
# save_photo
# ---------------------------------------------------------------------------


def test_save_photo_jpeg_cree_fichier_et_retourne_key():
    img = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
    key, size = photo_storage.save_photo(img, "image/jpeg")
    assert key is not None
    assert key.endswith(".jpg")
    assert size == len(img)
    path = photo_storage.get_upload_dir() / key
    assert path.exists()
    assert path.read_bytes() == img


def test_save_photo_extensions_par_mime():
    for mime, ext in [
        ("image/jpeg", ".jpg"),
        ("image/png", ".png"),
        ("image/webp", ".webp"),
        ("image/gif", ".gif"),
    ]:
        key, _ = photo_storage.save_photo(b"x", mime)
        assert key is not None and key.endswith(ext)


def test_save_photo_mime_inconnu_extension_bin():
    """Mime non listé → extension .bin (le router valide en amont
    de toute façon, c'est juste une garantie de robustesse)."""
    key, _ = photo_storage.save_photo(b"x", "application/octet-stream")
    assert key is not None and key.endswith(".bin")


def test_save_photo_bytes_vides_retourne_none():
    key, size = photo_storage.save_photo(b"", "image/jpeg")
    assert key is None
    assert size == 0


def test_save_photo_keys_uniques():
    """Deux save successifs → 2 clés distinctes (UUID)."""
    k1, _ = photo_storage.save_photo(b"a", "image/png")
    k2, _ = photo_storage.save_photo(b"b", "image/png")
    assert k1 != k2


def test_save_photo_mode_degrade_si_dir_non_writable(monkeypatch, tmp_path):
    """Si _ensure_dir_writable renvoie False → (None, 0) sans crash.
    Simule un Volume non monté."""
    monkeypatch.setattr(photo_storage, "_ensure_dir_writable", lambda d: False)
    key, size = photo_storage.save_photo(b"img", "image/jpeg")
    assert key is None
    assert size == 0


# ---------------------------------------------------------------------------
# get_photo_path
# ---------------------------------------------------------------------------


def test_get_photo_path_existe():
    key, _ = photo_storage.save_photo(b"data", "image/png")
    path = photo_storage.get_photo_path(key)
    assert path is not None
    assert path.read_bytes() == b"data"


def test_get_photo_path_inexistant_retourne_none():
    assert photo_storage.get_photo_path("nope.jpg") is None


def test_get_photo_path_protege_contre_path_traversal():
    """Tentatives d'évasion via ../ ou / dans la clé → None."""
    for bad in ["../etc/passwd", "..\\..\\windows\\system32", "/etc/hosts",
                "subdir/file.jpg", "..", ""]:
        assert photo_storage.get_photo_path(bad) is None


def test_get_photo_path_si_dossier_pas_fichier_retourne_none(tmp_path):
    """Si le path résolu est un répertoire (pas un fichier) → None."""
    # On crée un sous-répertoire qui ressemble à une clé valide
    upload_dir = photo_storage.get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    fake_key_dir = upload_dir / "abc123.jpg"
    fake_key_dir.mkdir()
    assert photo_storage.get_photo_path("abc123.jpg") is None


# ---------------------------------------------------------------------------
# delete_photo
# ---------------------------------------------------------------------------


def test_delete_photo_supprime_fichier():
    key, _ = photo_storage.save_photo(b"data", "image/jpeg")
    path = photo_storage.get_upload_dir() / key
    assert path.exists()
    assert photo_storage.delete_photo(key) is True
    assert not path.exists()


def test_delete_photo_inexistant_retourne_false():
    assert photo_storage.delete_photo("nope.jpg") is False


def test_delete_photo_key_none_retourne_false():
    assert photo_storage.delete_photo(None) is False
    assert photo_storage.delete_photo("") is False


def test_delete_photo_path_traversal_protege():
    assert photo_storage.delete_photo("../etc/passwd") is False


# ---------------------------------------------------------------------------
# Intégration : save → get → delete cycle complet
# ---------------------------------------------------------------------------


def test_cycle_save_get_delete():
    key, size = photo_storage.save_photo(b"hello world", "image/png")
    assert key is not None and size == 11

    path = photo_storage.get_photo_path(key)
    assert path is not None
    assert path.read_bytes() == b"hello world"

    assert photo_storage.delete_photo(key) is True
    assert photo_storage.get_photo_path(key) is None
