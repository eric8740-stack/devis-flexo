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
    AnalysePhotoRequest,
    AnalysePhotoResponse,
)
from app.services.ia.analyse_photo import analyser_photo_etiquette
from app.services.ia.client import DEFAULT_MODEL, IAClientError


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
