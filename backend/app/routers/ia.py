"""Router /api/ia — Sprint 13 Lot S13.E.3 (POC FlexoCheck).

1 endpoint :
  - POST /api/ia/analyser-photo
        Recoit une image base64 + mime_type, decode, appelle Claude API
        via le service analyser_photo_etiquette (S13.E.1), persiste le
        resultat en BDD (S13.E.2), renvoie l'id + payload.

Protege par require_module('flexocheck') (decision strategique du brief :
tous les modules IA appartiennent a FlexoCheck, meme l'analyse photo
etiquette qui pourrait sembler FlexoCompare-flavor).

Decisions :
  - Pas d'integration Vercel Blob ici (MVP) : on ne stocke pas la photo
    brute. Le payload Claude est la valeur de fond. Si on a besoin de
    re-analyser ou d'archiver pour audit, Sprint 14+ ajoutera l'upload
    vers Vercel Blob avant l'appel Claude.
  - mime_type validation cote schema + service (defense en profondeur).
  - On tolere les deux formats d'image_base64 : raw ou avec prefix
    'data:image/jpeg;base64,...' (le frontend utilise souvent FileReader
    qui produit le prefix).
  - 502 Bad Gateway si Claude API echoue (vs 500 generique) — c'est un
    upstream service failure, le client doit savoir que ce n'est pas son
    erreur.
"""
import base64
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_module
from app.models import AnalysePhotoEtiquette, User
from app.schemas.ia import (
    MIME_TYPES_AUTORISES,
    AnalysePhotoDetail,
    AnalysePhotoListItem,
    AnalysePhotoListResponse,
    AnalysePhotoRequest,
    AnalysePhotoResponse,
)
from app.services.ia.analyse_photo import analyser_photo_etiquette
from app.services.ia.client import DEFAULT_MODEL, IAClientError
from app.services.ia.photo_storage import (
    delete_photo,
    get_photo_path,
    save_photo,
)


router = APIRouter(prefix="/api/ia", tags=["ia"])


_DATA_URL_PREFIX = re.compile(r"^data:image/[a-z]+;base64,", re.IGNORECASE)


def _decoder_image_base64(image_base64: str) -> bytes:
    """Decode base64 (avec ou sans prefix data:). Leve HTTPException 422
    si invalide."""
    nettoye = _DATA_URL_PREFIX.sub("", image_base64).strip()
    try:
        return base64.b64decode(nettoye, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"image_base64 invalide : {exc}",
        ) from exc


@router.post("/analyser-photo", response_model=AnalysePhotoResponse)
def post_analyser_photo(
    payload: AnalysePhotoRequest,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
) -> AnalysePhotoResponse:
    """Analyse une photo d'étiquette via Claude API multimodal.

    Pipeline :
      1. Valide le mime_type (autorisés : image/jpeg | png | webp | gif).
      2. Décode l'image base64.
      3. Appelle le service analyser_photo_etiquette (S13.E.1) qui
         charge le prompt, envoie à Claude, parse + valide le JSON.
      4. Persiste en BDD (analyse_photo_etiquette, scopée tenant).
      5. Retourne l'id + payload.

    Codes erreurs :
      - 403 si user n'a pas le module flexocheck (require_module)
      - 422 si mime invalide ou base64 corrompu
      - 502 si Claude API echoue (cle absente, reponse vide, JSON invalide)
    """
    # Validation mime (defense en profondeur — pydantic peut etre bypasse
    # par un client mal codé qui force "image/svg" malgre le schema)
    if payload.mime_type not in MIME_TYPES_AUTORISES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"mime_type '{payload.mime_type}' non supporte. "
                f"Attendus : {list(MIME_TYPES_AUTORISES)}"
            ),
        )

    image_bytes = _decoder_image_base64(payload.image_base64)
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 vide apres decodage",
        )

    # Persistance physique de la photo AVANT l'appel IA — comme ça si Claude
    # échoue, on garde quand même la photo pour audit / re-essai éventuel.
    # En mode degrade (Volume Railway non monte), image_key=None et l'analyse
    # continue sans photo physique (cf. photo_storage.save_photo docstring).
    image_key, image_size = save_photo(image_bytes, payload.mime_type)

    try:
        resultats = analyser_photo_etiquette(image_bytes, payload.mime_type)
    except IAClientError as exc:
        # Persistance d'une row 'erreur' pour audit/analytique (V2 utile
        # pour mesurer le taux d'echec et identifier les patterns).
        # On garde tracabilite meme en cas d'echec.
        analyse_err = AnalysePhotoEtiquette(
            entreprise_id=user.entreprise_id,
            user_id=user.id,
            devis_id=payload.devis_id,
            photo_mime_type=payload.mime_type,
            photo_url=None,
            image_filename=payload.image_filename,
            image_key=image_key,
            image_size_bytes=image_size,
            resultats_ia={},  # JSON vide mais NOT NULL
            erreur=str(exc),
            model_utilise=DEFAULT_MODEL,
        )
        db.add(analyse_err)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Analyse IA echouee : {exc}",
        ) from exc

    # Persistance du succes
    analyse = AnalysePhotoEtiquette(
        entreprise_id=user.entreprise_id,
        user_id=user.id,
        devis_id=payload.devis_id,
        photo_mime_type=payload.mime_type,
        photo_url=None,
        image_filename=payload.image_filename,
        image_key=image_key,
        image_size_bytes=image_size,
        resultats_ia=resultats,
        niveau_confiance=resultats.get("niveau_confiance"),
        nombre_couleurs_distinctes=resultats.get("nombre_couleurs_distinctes"),
        model_utilise=DEFAULT_MODEL,
    )
    db.add(analyse)
    db.commit()
    db.refresh(analyse)

    return AnalysePhotoResponse(
        id=analyse.id,
        resultats_ia=analyse.resultats_ia,
        niveau_confiance=analyse.niveau_confiance or "moyen",
        nombre_couleurs_distinctes=analyse.nombre_couleurs_distinctes,
        model_utilise=analyse.model_utilise,
        created_at=analyse.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Historique des analyses photo (feat-historique-analyses)
# ---------------------------------------------------------------------------


def _to_list_item(row: AnalysePhotoEtiquette) -> AnalysePhotoListItem:
    return AnalysePhotoListItem(
        id=row.id,
        image_filename=row.image_filename,
        image_key=row.image_key,
        photo_mime_type=row.photo_mime_type,
        image_size_bytes=row.image_size_bytes,
        niveau_confiance=row.niveau_confiance,
        nombre_couleurs_distinctes=row.nombre_couleurs_distinctes,
        erreur=row.erreur,
        created_at=row.created_at.isoformat(),
    )


def _to_detail(row: AnalysePhotoEtiquette) -> AnalysePhotoDetail:
    return AnalysePhotoDetail(
        id=row.id,
        image_filename=row.image_filename,
        image_key=row.image_key,
        photo_mime_type=row.photo_mime_type,
        image_size_bytes=row.image_size_bytes,
        resultats_ia=row.resultats_ia or {},
        niveau_confiance=row.niveau_confiance,
        nombre_couleurs_distinctes=row.nombre_couleurs_distinctes,
        model_utilise=row.model_utilise,
        erreur=row.erreur,
        devis_id=row.devis_id,
        created_at=row.created_at.isoformat(),
    )


@router.get("/analyses", response_model=AnalysePhotoListResponse)
def list_analyses(
    page: int = 1,
    limit: int = 20,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
) -> AnalysePhotoListResponse:
    """Liste paginée des analyses photo du tenant courant.

    Scope strict sur user.entreprise_id, tri created_at DESC.
    Pagination 1-indexée : `?page=1&limit=20` par défaut.
    """
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        # Borne pour éviter `?limit=10000` qui mettrait le serveur à plat
        limit = 20

    base_q = db.query(AnalysePhotoEtiquette).filter_by(
        entreprise_id=user.entreprise_id
    )
    total = base_q.count()
    rows = (
        # Tie-break par id desc : deux analyses créées dans la même ms
        # (cas réaliste en tests, possible aussi en prod) → la plus
        # récente sort en premier de façon déterministe.
        base_q.order_by(
            AnalysePhotoEtiquette.created_at.desc(),
            AnalysePhotoEtiquette.id.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return AnalysePhotoListResponse(
        items=[_to_list_item(r) for r in rows],
        page=page,
        limit=limit,
        total=total,
    )


@router.get("/analyses/{analyse_id}", response_model=AnalysePhotoDetail)
def get_analyse(
    analyse_id: int,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
) -> AnalysePhotoDetail:
    """Détail complet d'une analyse passée.

    Multi-tenant : 404 si la row appartient à un autre tenant (PAS 403,
    pour ne pas leak l'existence des ids cross-tenant).
    """
    row = (
        db.query(AnalysePhotoEtiquette)
        .filter_by(id=analyse_id, entreprise_id=user.entreprise_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse introuvable",
        )
    return _to_detail(row)


@router.delete(
    "/analyses/{analyse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_analyse(
    analyse_id: int,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
) -> None:
    """Suppression définitive (hard delete, conforme RGPD).

    Supprime la row DB ET le fichier disque associé. Idempotent côté
    fichier (delete_photo ne lève jamais). 404 si row inexistante ou
    appartenant à un autre tenant.
    """
    row = (
        db.query(AnalysePhotoEtiquette)
        .filter_by(id=analyse_id, entreprise_id=user.entreprise_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse introuvable",
        )
    # Capture image_key avant suppression DB pour cleanup disque post-commit
    image_key = row.image_key
    db.delete(row)
    db.commit()
    if image_key:
        delete_photo(image_key)


@router.get("/photos/{image_key}")
def serve_photo(
    image_key: str,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Sert le fichier image d'une analyse via FileResponse.

    Multi-tenant strict : on vérifie d'abord qu'il existe une row
    analyse_photo_etiquette avec ce image_key ET entreprise_id du user.
    Sinon 404 — pas 403, pour ne pas leak la liste des keys cross-tenant.

    Content-Type basé sur photo_mime_type stocké en BDD (pas inferé
    de l'extension fichier — évite le content sniffing).
    """
    row = (
        db.query(AnalysePhotoEtiquette)
        .filter_by(image_key=image_key, entreprise_id=user.entreprise_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo introuvable",
        )
    path = get_photo_path(image_key)
    if path is None:
        # Row existe mais fichier disque absent (Volume non monte, ou
        # ancienne analyse pre-feat). 404 pour cohérence cote client.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier photo non disponible sur disque",
        )
    # Import local pour éviter d'alourdir le head du module avec un
    # symbole rarement utilisé hors de cet endpoint.
    from fastapi.responses import FileResponse

    return FileResponse(
        path,
        media_type=row.photo_mime_type or "application/octet-stream",
        filename=row.image_filename or image_key,
    )
