"""Service de stockage des photos d'analyse — feat historique analyses.

Stratégie :
  - Storage local : disque Railway Volume monté sur /mnt/uploads/photos
    (path configurable via env PHOTO_UPLOAD_DIR pour dev local).
  - Naming : "{uuid4}.{ext}" — collision-free + permet de poser l'image_key
    en UNIQUE en BDD sans collision.
  - Mode dégradé : si le répertoire n'est pas writable (Volume non monté
    sur Railway, par ex.), on log un warning et on retourne (None, 0).
    L'analyse Claude s'effectue quand même et persiste les métadonnées,
    juste sans photo physique. Permet de déployer le code AVANT que le
    Volume soit configuré, sans casser l'API d'analyse.

Pas d'async (le reste du projet est sync ; pas la peine d'introduire
aiofiles pour des fichiers < 10 Mo sur un endpoint déjà gated par
l'appel Claude qui prend 2-10 s).

Migration future vers Cloudflare R2 / Vercel Blob (Phase 2 du prompt) :
remplacer save_photo / get_photo_path / delete_photo par leurs équivalents
distants — l'interface module reste identique côté appelants.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


# Mapping mime → extension. On garde court (4 types supportés par le SDK
# Anthropic et validés en amont par le router /api/ia/analyser-photo).
_EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def get_upload_dir() -> Path:
    """Renvoie le répertoire de stockage configuré (env var ou default).

    Default Railway prod : /mnt/uploads/photos (à mapper sur un Volume).
    Default dev local : <repo>/backend/.uploads/photos (gitignore).
    """
    env_path = os.getenv("PHOTO_UPLOAD_DIR")
    if env_path:
        return Path(env_path)
    # En dev local, on stocke dans .uploads à la racine du backend pour
    # ne pas pourrir le système de fichiers utilisateur.
    return Path(__file__).resolve().parents[3] / ".uploads" / "photos"


def _ensure_dir_writable(directory: Path) -> bool:
    """Tente de créer le répertoire et de tester l'écriture. Renvoie False
    en cas d'erreur (volume non monté, permissions, etc.)."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        # Touch test : crée un fichier temp puis le supprime
        test_file = directory / f".write_test_{uuid.uuid4().hex[:8]}"
        test_file.write_bytes(b"")
        test_file.unlink()
        return True
    except OSError as exc:
        logger.warning(
            "photo_storage : répertoire %s non writable (%s). "
            "Les photos ne seront PAS persistées physiquement, "
            "l'analyse continuera sans archivage. "
            "Configurer Railway Volume sur ce mount point pour activer.",
            directory,
            exc,
        )
        return False


def save_photo(file_bytes: bytes, mime: str) -> tuple[str | None, int]:
    """Sauve la photo sur disque, renvoie (image_key, size_bytes).

    image_key est de la forme "{uuid4}.{ext}". Cette clé sert ensuite
    à servir le fichier via GET /api/photos/{key}.

    Si le répertoire n'est pas writable (Volume non monté, etc.) →
    renvoie (None, 0). L'appelant doit gérer le cas image_key=None
    (= analyse persistée sans photo physique, mode dégradé).
    """
    if not file_bytes:
        return None, 0

    upload_dir = get_upload_dir()
    if not _ensure_dir_writable(upload_dir):
        return None, 0

    ext = _EXT_BY_MIME.get(mime, ".bin")
    key = f"{uuid.uuid4().hex}{ext}"
    path = upload_dir / key

    try:
        path.write_bytes(file_bytes)
    except OSError as exc:
        logger.warning(
            "photo_storage : échec écriture %s (%s). "
            "Analyse persistée sans photo.",
            path,
            exc,
        )
        return None, 0

    return key, len(file_bytes)


def get_photo_path(image_key: str) -> Path | None:
    """Renvoie le chemin disque d'une photo si elle existe, sinon None.

    Validation basique de la clé pour ne pas servir n'importe quoi
    (path traversal protection : pas de '/' ni '..' dans la clé).
    """
    if not image_key or "/" in image_key or "\\" in image_key or ".." in image_key:
        return None
    path = get_upload_dir() / image_key
    if not path.exists() or not path.is_file():
        return None
    return path


def delete_photo(image_key: str | None) -> bool:
    """Supprime la photo du disque. Renvoie True si supprimée, False
    sinon (n'existe pas, ou path invalide). Ne lève jamais — un échec
    de suppression ne doit pas bloquer la suppression de la row DB."""
    if not image_key:
        return False
    path = get_photo_path(image_key)
    if path is None:
        return False
    try:
        path.unlink()
        return True
    except OSError as exc:
        logger.warning(
            "photo_storage : échec suppression %s (%s)", path, exc
        )
        return False
