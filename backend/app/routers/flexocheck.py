"""Router /api/flexocheck — Sprint 15 Lot 3 (Contrôle BAT IA).

7 endpoints (+ 1 serve-blob interne) sous `/api/flexocheck/`, tous
protégés par `Depends(require_module("flexocheck"))` et scopés
multi-tenant sur `user.entreprise_id`.

| Méthode | Path | Rôle |
|---|---|---|
| POST | /controle-bat/upload-bat | Upload BAT (PDF/image, max 10 Mo) |
| GET | /productions-actives | Liste des devis en production du tenant |
| GET | /controle-bat/contexte/{devis_id} | Contexte pré-contrôle (BAT + métadonnées) |
| POST | /controle-bat/ | Upload photo 1er tirage → analyse IA → ControleBat |
| GET | /controle-bat/{devis_id} | Toutes les tentatives d'un devis |
| POST | /controle-bat/{id}/decision | Enregistre la décision finale |
| POST | /controle-bat/{id}/retirage | Nouvelle tentative photo + IA, tentative+1 |
| GET | /blobs/{image_key} | Sert BAT/photo (FileResponse, scope multi-tenant) |

Choix de scope :
  - Statut « en production » : Devis n'a pas (encore) de statut dédié,
    on retient `statut = 'valide'` comme proxy. Documenté côté schema
    ProductionActiveItem.
  - Retirage : prend une photo multipart (comme le contrôle initial),
    crée un ControleBat tentative_numero+1 avec
    `controle_bat_precedent_id={id}`. Cohérent avec le modèle Lot 1
    (premier_tirage_url NOT NULL).
  - `decision_finale` initiale = "en_attente" (cf. brief « rends la
    colonne nullable ou utilise 'en_attente' » — choix : NOT NULL +
    valeur réservée, plus défensif côté requêtes).
  - Service IA indisponible → 503 (clé absente, JSON Claude
    inexploitable, etc. — toute IAClientError).
  - Stockage local Volume Railway via `photo_storage.save_photo()`
    et URLs `/api/flexocheck/blobs/{image_key}`. V2 = migration vers
    Vercel Blob (URLs publiques externes, structure inchangée côté
    contrat HTTP).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_module
from app.models import (
    BAT_MIME_TYPES_AUTORISES,
    BatReference,
    Client,
    ControleBat,
    Devis,
    Machine,
    User,
)
from app.schemas.controle_bat import (
    AlerteSensEnroulement,
    BatUploadResponse,
    ControleBatAnalyseResponse,
    ControleBatContexte,
    ControleBatDetail,
    DecisionFinaleIn,
    EcartDetail,
    OptionCorrectionSens,
    ProductionActiveItem,
    ProductionsActivesResponse,
)
from app.services.coherence_sens import (
    diagnostiquer_coherence,
    sens_demande_du_devis,
)
from app.services.ia.client import IAClientError
from app.services.ia.controle_bat import comparer_bat_vs_tirage
from app.services.ia.photo_storage import (
    get_photo_path,
    save_photo,
)
from app.services.scope_service import get_or_404_scoped

router = APIRouter(prefix="/api/flexocheck", tags=["flexocheck"])


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------


TAILLE_MAX_BAT_OCTETS = 10 * 1024 * 1024  # 10 Mo (PDF / image BAT)
TAILLE_MAX_PHOTO_OCTETS = 15 * 1024 * 1024  # 15 Mo (photo 1er tirage)

# MIME types autorisés pour la photo du 1er tirage : 3 formats images
# acceptés par Claude API multimodal (cf. wrapper client.py). On retire
# image/gif (peu pertinent pour une photo presse) et on n'accepte pas le
# PDF (Claude ne peut pas raisonner sur un PDF avec messages.images).
PHOTO_TIRAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

# Seuil de tentatives à partir duquel le retirage déclenche l'alerte chef
# d'atelier côté UI (cf. brief Lot 3 § endpoint 7).
TENTATIVES_SEUIL_ALERTE_CHEF = 3


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


def _build_blob_url(image_key: str | None) -> str | None:
    """Construit l'URL servie par `GET /api/flexocheck/blobs/{key}`.

    Renvoie None si pas de clé (mode dégradé Volume non monté).
    """
    if not image_key:
        return None
    return f"/api/flexocheck/blobs/{image_key}"


def _build_alerte_sens(
    message: str | None,
    action_recommandee: str | None = None,
) -> AlerteSensEnroulement | None:
    """Enveloppe `alerte_sens_enroulement` en objet structuré avec
    auto-sélection (Lot 4) de l'action recommandée.

    Si `message` est None, retourne None (pas d'alerte). Sinon construit
    les 3 options de correction standards (codes alignés sur
    `ACTIONS_CORRECTION_SENS` du modèle). L'option dont le `code` matche
    `action_recommandee` reçoit `recommandee=True` et est placée en
    premier dans la liste — l'UI met cette option en avant.
    """
    if not message:
        return None

    options = [
        OptionCorrectionSens(
            code="inversion_cliche",
            libelle="Inverser le cliché",
            description=(
                "Remettre le cliché à l'endroit sur la presse. "
                "Tirage à reprendre après inversion."
            ),
            recommandee=(action_recommandee == "inversion_cliche"),
        ),
        OptionCorrectionSens(
            code="ajustement_rebobineuse",
            libelle="Ajuster la rebobineuse",
            description=(
                "Reconfigurer la rebobineuse pour produire le sens "
                "d'enroulement demandé sans toucher au cliché."
            ),
            recommandee=(action_recommandee == "ajustement_rebobineuse"),
        ),
        OptionCorrectionSens(
            code="confirmation_client",
            libelle="Demander confirmation client",
            description=(
                "Contacter le client pour valider le sens observé "
                "comme acceptable malgré l'écart au BAT."
            ),
            recommandee=(action_recommandee == "confirmation_client"),
        ),
    ]
    # Stable sort : option recommandée en premier, autres dans l'ordre
    # de déclaration. `False < True` donc on inverse via `not`.
    options.sort(key=lambda o: not o.recommandee)
    return AlerteSensEnroulement(message=message, options_correction=options)


def _ecarts_to_detail(ecarts: Iterable[dict] | None) -> list[EcartDetail]:
    """Cast JSON brut en list[EcartDetail] (no-op si ecarts vide/None)."""
    if not ecarts:
        return []
    return [EcartDetail.model_validate(e) for e in ecarts]


def _resultats_to_lists(
    resultats: dict | None, key: str
) -> list[str]:
    """Extrait une liste de strings d'un payload JSON (None → [])."""
    if not resultats:
        return []
    val = resultats.get(key)
    if not isinstance(val, list):
        return []
    return [str(v) for v in val if v is not None]


def _to_analyse_response(
    cb: ControleBat,
    alerte_chef_atelier: bool | None = None,
) -> ControleBatAnalyseResponse:
    """Convertit une row ControleBat en payload de réponse analyse.

    Re-pioche les champs liste depuis `resultats_comparaison` (JSONB) pour
    éviter de les dupliquer en colonnes dédiées sur le modèle.

    Sprint 15 Lot 4 — construction de `alerte_sens_enroulement` :
      1. On recalcule le diagnostic à partir des sens persistés sur la
         row (canonique, défensif vs drift entre stockage et réponse).
      2. Si le diagnostic identifie une incohérence (message non-null)
         → l'alerte porte ce message + option recommandée auto-sélectionnée.
      3. Sinon, fallback sur l'alerte brute renvoyée par l'IA (Lot 3) :
         couvre le cas où le sens demandé est absent (info insuffisante
         pour notre diagnostic) mais l'IA a vu un autre type d'anomalie.
    """
    resultats = cb.resultats_comparaison or {}

    diagnostic = diagnostiquer_coherence(
        sens_demande=cb.sens_enroulement_demande,
        sens_detecte=cb.sens_sortie_detecte,
        niveau_confiance=cb.niveau_confiance,
    )
    if diagnostic["message_alerte"]:
        alerte = _build_alerte_sens(
            diagnostic["message_alerte"],
            action_recommandee=diagnostic["action_correction_sens"],
        )
    else:
        alerte_brut = resultats.get("alerte_sens_enroulement")
        alerte = _build_alerte_sens(
            alerte_brut if isinstance(alerte_brut, str) else None,
            action_recommandee=cb.action_correction_sens,
        )

    return ControleBatAnalyseResponse(
        controle_id=cb.id,
        devis_id=cb.devis_id,
        tentative=cb.tentative_numero,
        score_conformite=cb.score_conformite,
        decision_recommandee=cb.decision_recommandee,
        niveau_confiance=cb.niveau_confiance,
        limites_analyse=_resultats_to_lists(resultats, "limites_analyse"),
        ecarts=_ecarts_to_detail(cb.ecarts_detectes),
        elements_conformes=_resultats_to_lists(resultats, "elements_conformes"),
        elements_manquants=_resultats_to_lists(resultats, "elements_manquants"),
        sens_enroulement_detecte=cb.sens_sortie_detecte,
        sens_enroulement_demande=cb.sens_enroulement_demande,
        alerte_sens_enroulement=alerte,
        alerte_chef_atelier=alerte_chef_atelier,
    )


def _designation_from_devis(devis: Devis) -> str:
    """Compose une désignation lisible (`numero` à défaut de champ
    business dédié sur Devis)."""
    return devis.numero


def _lookup_bat_reference(
    db: Session, entreprise_id: int, devis_id: int
) -> BatReference | None:
    return (
        db.query(BatReference)
        .filter_by(entreprise_id=entreprise_id, devis_id=devis_id)
        .first()
    )


def _ecarts_compteurs(ecarts: Iterable[dict] | None) -> tuple[int, int]:
    """Compte les écarts majeurs + critiques (= majeurs) vs mineurs.

    Convention modèle : `nb_ecarts_majeurs` inclut critique + majeur,
    `nb_ecarts_mineurs` = mineur. Évite de poser une 3e colonne pour
    « critique ». Le détail reste accessible via `ecarts_detectes`.
    """
    majeurs = 0
    mineurs = 0
    for e in ecarts or []:
        g = e.get("gravite")
        if g in ("critique", "majeur"):
            majeurs += 1
        elif g == "mineur":
            mineurs += 1
    return majeurs, mineurs


# ---------------------------------------------------------------------------
# Endpoint 0 (transverse) — serve blob (BAT + photo tirage)
# ---------------------------------------------------------------------------


@router.get("/blobs/{image_key}")
def serve_blob(
    image_key: str,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Sert un fichier (BAT ou photo de tirage) via FileResponse.

    Multi-tenant strict : on vérifie que `image_key` appartient soit à
    une `bat_reference`, soit à un `controle_bat` du tenant courant.
    404 si l'image n'appartient à aucune des deux tables OU appartient
    à un autre tenant (anti-énumération).
    """
    bat_row = (
        db.query(BatReference)
        .filter_by(image_key=image_key, entreprise_id=user.entreprise_id)
        .first()
    )
    if bat_row is not None:
        mime = bat_row.bat_mime_type
        filename = bat_row.bat_filename
    else:
        cb_row = (
            db.query(ControleBat)
            .filter_by(
                premier_tirage_image_key=image_key,
                entreprise_id=user.entreprise_id,
            )
            .first()
        )
        if cb_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier introuvable",
            )
        # Pour les photos tirage on a uniquement le mime côté upload —
        # on l'a perdu (pas stocké). On déduit du suffixe du fichier.
        mime = _mime_from_key(image_key)
        filename = image_key

    path = get_photo_path(image_key)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non disponible sur disque",
        )
    from fastapi.responses import FileResponse

    return FileResponse(
        path,
        media_type=mime or "application/octet-stream",
        filename=filename or image_key,
    )


def _mime_from_key(image_key: str) -> str:
    """Déduit un mime type approximatif depuis l'extension du image_key.

    image_key est de la forme `{uuid4}.{ext}` (cf. photo_storage). On
    couvre les 4 extensions image stockables + PDF.
    """
    if image_key.endswith(".pdf"):
        return "application/pdf"
    if image_key.endswith(".png"):
        return "image/png"
    if image_key.endswith(".webp"):
        return "image/webp"
    if image_key.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


# ---------------------------------------------------------------------------
# Endpoint 1 — upload BAT
# ---------------------------------------------------------------------------


@router.post(
    "/controle-bat/upload-bat",
    response_model=BatUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_bat(
    devis_id: int = Form(..., ge=1),
    file: UploadFile = File(...),
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Upload du BAT validé client (PDF ou image) lié à un devis.

    - 422 si `devis_id` ne correspond pas à un devis du tenant.
    - 415 si MIME hors liste autorisée.
    - 413 si fichier > 10 Mo.
    - Idempotent : un ré-upload remplace l'ancien BAT (row UPDATE).

    NB : on lit `file.size` après lecture des bytes (l'attribut size de
    UploadFile peut être None côté Starlette selon l'origine). On lit
    en mémoire (10 Mo max, acceptable) puis on délègue à photo_storage.
    """
    # 1. Validation devis_id appartient au tenant
    devis = (
        db.query(Devis)
        .filter_by(id=devis_id, entreprise_id=user.entreprise_id)
        .first()
    )
    if devis is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Devis {devis_id} introuvable pour ce tenant",
        )

    # 2. Validation MIME
    mime = file.content_type or "application/octet-stream"
    if mime not in BAT_MIME_TYPES_AUTORISES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Type {mime!r} non supporté pour BAT. "
                f"Attendus : {sorted(BAT_MIME_TYPES_AUTORISES)}"
            ),
        )

    # 3. Lecture + check taille
    contenu = file.file.read()
    if len(contenu) > TAILLE_MAX_BAT_OCTETS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"BAT trop volumineux (max {TAILLE_MAX_BAT_OCTETS // (1024*1024)} Mo)",
        )

    # 4. Stockage physique + upsert BatReference
    image_key, size = save_photo(contenu, mime)
    bat_url = _build_blob_url(image_key) or ""

    existante = _lookup_bat_reference(db, user.entreprise_id, devis_id)
    now = datetime.now(timezone.utc)
    if existante is not None:
        existante.bat_url = bat_url
        existante.image_key = image_key
        existante.bat_filename = file.filename
        existante.bat_mime_type = mime
        existante.bat_size_bytes = size
        existante.bat_uploaded_at = now
        row = existante
    else:
        row = BatReference(
            entreprise_id=user.entreprise_id,
            devis_id=devis_id,
            bat_url=bat_url,
            image_key=image_key,
            bat_filename=file.filename,
            bat_mime_type=mime,
            bat_size_bytes=size,
            bat_uploaded_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)

    return BatUploadResponse.model_validate(row)


# ---------------------------------------------------------------------------
# Endpoint 2 — productions-actives
# ---------------------------------------------------------------------------


@router.get("/productions-actives", response_model=ProductionsActivesResponse)
def list_productions_actives(
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Liste des devis en production du tenant courant.

    Proxy actuel du statut « en production » : Devis.statut == 'valide'.
    Documenté côté schema. Si un statut dédié est introduit en Sprint 16+,
    adapter le filtre ici seulement.

    Tri date_creation DESC + id DESC (tie-break déterministe).
    """
    rows = (
        db.query(Devis, Client, Machine, BatReference)
        .outerjoin(Client, Devis.client_id == Client.id)
        .join(Machine, Devis.machine_id == Machine.id)
        .outerjoin(
            BatReference,
            (BatReference.devis_id == Devis.id)
            & (BatReference.entreprise_id == user.entreprise_id),
        )
        .filter(
            Devis.entreprise_id == user.entreprise_id,
            Devis.statut == "valide",
        )
        .order_by(Devis.date_creation.desc(), Devis.id.desc())
        .all()
    )
    items = [
        ProductionActiveItem(
            devis_id=devis.id,
            client=(client.raison_sociale if client is not None else None),
            designation=_designation_from_devis(devis),
            machine=machine.nom,
            bat_reference_uploaded=bat_ref is not None,
        )
        for devis, client, machine, bat_ref in rows
    ]
    return ProductionsActivesResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# Endpoint 3 — contexte pré-contrôle
# ---------------------------------------------------------------------------


@router.get(
    "/controle-bat/contexte/{devis_id}",
    response_model=ControleBatContexte,
)
def get_contexte(
    devis_id: int,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Renvoie le contexte d'un devis (BAT + métadonnées) pour l'écran
    pré-contrôle. `bat_url` / `bat_mime_type` sont None si aucun BAT
    n'est encore uploadé."""
    devis = get_or_404_scoped(db, Devis, devis_id, user)
    client = (
        db.query(Client).filter_by(id=devis.client_id).first()
        if devis.client_id
        else None
    )
    machine = db.query(Machine).filter_by(id=devis.machine_id).first()
    if machine is None:
        # Devis a machine_id NOT NULL FK, donc improbable — défense en
        # profondeur : on ne veut pas servir un retour incohérent.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Machine du devis introuvable",
        )
    bat_ref = _lookup_bat_reference(db, user.entreprise_id, devis_id)
    return ControleBatContexte(
        devis_id=devis.id,
        devis_numero=devis.numero,
        client_nom=client.raison_sociale if client else None,
        designation=_designation_from_devis(devis),
        machine_nom=machine.nom,
        bat_url=bat_ref.bat_url if bat_ref else None,
        bat_mime_type=bat_ref.bat_mime_type if bat_ref else None,
    )


# ---------------------------------------------------------------------------
# Endpoint 4 — POST /controle-bat/ : upload photo tirage + analyse IA
# ---------------------------------------------------------------------------


def _lire_bat_bytes(bat_ref: BatReference) -> bytes:
    """Lit le binaire BAT depuis le stockage local.

    Lève 409 si le binaire n'est plus disponible sur disque (Volume non
    monté en prod, ou row historique pré-Volume).
    """
    if not bat_ref.image_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="BAT enregistré mais binaire indisponible sur disque",
        )
    path = get_photo_path(bat_ref.image_key)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="BAT enregistré mais fichier introuvable sur disque",
        )
    return path.read_bytes()


def _executer_controle(
    *,
    db: Session,
    user: User,
    devis: Devis,
    bat_ref: BatReference,
    photo_bytes: bytes,
    photo_mime: str,
    sens_demande: str | None,
    tentative_numero: int,
    controle_bat_precedent_id: int | None,
) -> ControleBat:
    """Pipeline interne partagé entre POST /controle-bat/ et /retirage.

    1. Lit le binaire BAT
    2. Appelle `comparer_bat_vs_tirage` (Lot 2) — 503 si IA indisponible
    3. Stocke la photo tirage
    4. Crée la row ControleBat (decision_finale="en_attente",
       decideur=user.nom_contact ou fallback email)
    """
    bat_bytes = _lire_bat_bytes(bat_ref)

    # Sprint 15 Lot 4 — fallback sens demandé : si l'opérateur n'a pas
    # explicité de sens en multipart, on lit le sens du 1er lot de
    # production du devis (interprétation : le client a validé le sens
    # au moment du chiffrage multi-lots). Reste None pour les devis
    # legacy mono-config sans LotProduction.
    if sens_demande is None:
        sens_demande = sens_demande_du_devis(db, devis.id)

    try:
        resultats = comparer_bat_vs_tirage(
            bat_image_bytes=bat_bytes,
            tirage_image_bytes=photo_bytes,
            sens_demande=sens_demande,
            bat_mime_type=bat_ref.bat_mime_type
            if bat_ref.bat_mime_type in {"image/jpeg", "image/png", "image/webp", "image/gif"}
            else "image/jpeg",
            tirage_mime_type=photo_mime,
        )
    except IAClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service IA indisponible : {exc}",
        ) from exc

    # Le service Lot 2 enrichit la réponse avec `cout_api_eur` (Decimal).
    # On l'extrait pour la column NUMERIC dédiée et on retire du dict avant
    # stockage JSON (Decimal n'est pas JSON-sérialisable par json natif).
    cout_api = resultats.pop("cout_api_eur", None)

    # Persistance photo tirage
    photo_key, _ = save_photo(photo_bytes, photo_mime)
    tirage_url = _build_blob_url(photo_key) or ""

    sens_struct = resultats.get("sens_sortie_detecte") or {}
    sens_resultant = sens_struct.get("sens_enroulement_resultant")

    # Sprint 15 Lot 4 — diagnostic métier vs convention SE1-SE8 (sacred
    # rotation_se en lecture seule). Surcharge l'info `coherence_avec_bat`
    # remontée par l'IA quand notre diagnostic peut trancher (sens demandé
    # + sens détecté tous deux connus). Sinon fallback sur l'IA.
    diagnostic = diagnostiquer_coherence(
        sens_demande=sens_demande,
        sens_detecte=sens_resultant if isinstance(sens_resultant, str) else None,
        niveau_confiance=resultats.get("niveau_confiance_analyse"),
    )
    if diagnostic["coherence_sens"] is not None:
        coherence = diagnostic["coherence_sens"]
    else:
        ia_coherence = sens_struct.get("coherence_avec_bat")
        coherence = ia_coherence if isinstance(ia_coherence, bool) else None
    action_correction = diagnostic["action_correction_sens"]

    majeurs, mineurs = _ecarts_compteurs(resultats.get("ecarts_detectes"))

    decideur = (user.nom_contact or user.email or "inconnu")[:200]

    cb = ControleBat(
        entreprise_id=user.entreprise_id,
        devis_id=devis.id,
        # BAT (copie depuis bat_ref pour figer l'historique au moment du
        # contrôle — un ré-upload BAT ultérieur ne réécrit pas l'analyse).
        bat_url=bat_ref.bat_url,
        bat_date_validation=bat_ref.bat_date_validation,
        bat_valide_par=bat_ref.bat_valide_par,
        # Photo tirage
        premier_tirage_url=tirage_url,
        premier_tirage_image_key=photo_key,
        premier_tirage_timestamp=datetime.now(timezone.utc),
        # Résultats IA
        resultats_comparaison=resultats,
        score_conformite=Decimal(str(resultats.get("score_conformite_global")))
        if resultats.get("score_conformite_global") is not None
        else None,
        decision_recommandee=resultats.get("decision_recommandee"),
        ecarts_detectes=resultats.get("ecarts_detectes") or [],
        nb_ecarts_majeurs=majeurs,
        nb_ecarts_mineurs=mineurs,
        niveau_confiance=resultats.get("niveau_confiance_analyse"),
        # Décision opérateur (initiale)
        decision_finale="en_attente",
        decideur=decideur,
        motif_decision=None,
        # Chaînage
        tentative_numero=tentative_numero,
        controle_bat_precedent_id=controle_bat_precedent_id,
        # Coût API
        cout_api_eur=cout_api,
        # Sens sortie (Lot 4 : diagnostic vs convention SE1-SE8)
        sens_sortie_detecte=sens_resultant if isinstance(sens_resultant, str) else None,
        sens_enroulement_demande=sens_demande,
        coherence_sens=coherence,
        action_correction_sens=action_correction,
    )
    db.add(cb)
    db.commit()
    db.refresh(cb)
    return cb


@router.post(
    "/controle-bat/",
    response_model=ControleBatAnalyseResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_controle_bat(
    devis_id: int = Form(..., ge=1),
    photo: UploadFile = File(...),
    sens_demande: str | None = Form(None, max_length=3),
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Upload photo 1er tirage → analyse IA Claude → crée ControleBat.

    Codes erreur :
      - 404 : devis inexistant pour ce tenant
      - 409 : BAT non encore uploadé pour ce devis (`upload-bat` requis avant)
      - 413 : photo > 15 Mo
      - 422 : mime non supporté (image/jpeg|png|webp uniquement)
      - 503 : IA indisponible (clé absente, JSON Claude invalide, etc.)
    """
    devis = (
        db.query(Devis)
        .filter_by(id=devis_id, entreprise_id=user.entreprise_id)
        .first()
    )
    if devis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devis {devis_id} introuvable",
        )

    bat_ref = _lookup_bat_reference(db, user.entreprise_id, devis_id)
    if bat_ref is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Aucun BAT rattaché au devis {devis_id}. "
                f"Faire d'abord POST /api/flexocheck/controle-bat/upload-bat."
            ),
        )

    mime = photo.content_type or "application/octet-stream"
    if mime not in PHOTO_TIRAGE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Type {mime!r} non supporté pour photo tirage. "
                f"Attendus : {sorted(PHOTO_TIRAGE_MIME_TYPES)}"
            ),
        )

    contenu = photo.file.read()
    if len(contenu) > TAILLE_MAX_PHOTO_OCTETS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo trop volumineuse (max {TAILLE_MAX_PHOTO_OCTETS // (1024*1024)} Mo)",
        )

    cb = _executer_controle(
        db=db,
        user=user,
        devis=devis,
        bat_ref=bat_ref,
        photo_bytes=contenu,
        photo_mime=mime,
        sens_demande=sens_demande,
        tentative_numero=1,
        controle_bat_precedent_id=None,
    )
    return _to_analyse_response(cb)


# ---------------------------------------------------------------------------
# Endpoint 5 — GET liste des contrôles d'un devis
# ---------------------------------------------------------------------------


@router.get(
    "/controle-bat/{devis_id}",
    response_model=list[ControleBatDetail],
)
def list_controles_devis(
    devis_id: int,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Liste toutes les tentatives d'un devis (ordre tentative_numero ASC).

    404 si le devis n'appartient pas au tenant. Liste vide si aucun
    contrôle effectué.
    """
    get_or_404_scoped(db, Devis, devis_id, user)
    rows = (
        db.query(ControleBat)
        .filter_by(entreprise_id=user.entreprise_id, devis_id=devis_id)
        .order_by(ControleBat.tentative_numero.asc(), ControleBat.id.asc())
        .all()
    )
    return [ControleBatDetail.model_validate(r) for r in rows]


# ---------------------------------------------------------------------------
# Endpoint 6 — POST /{id}/decision
# ---------------------------------------------------------------------------


@router.post(
    "/controle-bat/{controle_id}/decision",
    response_model=ControleBatDetail,
)
def post_decision(
    controle_id: int,
    payload: DecisionFinaleIn,
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Enregistre la décision finale de l'opérateur sur un contrôle."""
    cb = get_or_404_scoped(db, ControleBat, controle_id, user)
    cb.decision_finale = payload.decision_finale
    cb.decideur = payload.decideur
    cb.motif_decision = payload.motif_decision
    db.commit()
    db.refresh(cb)
    return ControleBatDetail.model_validate(cb)


# ---------------------------------------------------------------------------
# Endpoint 7 — POST /{id}/retirage : nouveau contrôle, tentative+1
# ---------------------------------------------------------------------------


@router.post(
    "/controle-bat/{controle_id}/retirage",
    response_model=ControleBatAnalyseResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_retirage(
    controle_id: int,
    photo: UploadFile = File(...),
    sens_demande: str | None = Form(None, max_length=3),
    user: User = Depends(require_module("flexocheck")),
    db: Session = Depends(get_db),
):
    """Crée un nouveau ControleBat (tentative+1, parent={controle_id}).

    Hypothèse d'usage : l'opérateur a corrigé la presse et photographié
    un nouveau tirage → cet endpoint accepte la nouvelle photo en
    multipart, ré-applique le pipeline IA, et chaîne via
    `controle_bat_precedent_id`. Cohérent avec
    `ControleBat.premier_tirage_url NOT NULL` (modèle Lot 1).

    Si la nouvelle tentative dépasse `TENTATIVES_SEUIL_ALERTE_CHEF` (3),
    `alerte_chef_atelier=true` est renvoyé dans la réponse pour que l'UI
    déclenche la notification chef d'atelier (pas d'envoi email backend
    dans ce sprint, cf. brief).

    Codes erreur identiques à POST /controle-bat/ (+ 404 si parent
    inexistant pour ce tenant).
    """
    parent = get_or_404_scoped(db, ControleBat, controle_id, user)

    bat_ref = _lookup_bat_reference(db, user.entreprise_id, parent.devis_id)
    if bat_ref is None:
        # Improbable car le parent a forcément été créé avec un BAT, mais
        # ce dernier peut avoir été supprimé entre temps (cascade devis).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="BAT du devis parent introuvable",
        )

    mime = photo.content_type or "application/octet-stream"
    if mime not in PHOTO_TIRAGE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Type {mime!r} non supporté pour photo tirage. "
                f"Attendus : {sorted(PHOTO_TIRAGE_MIME_TYPES)}"
            ),
        )

    contenu = photo.file.read()
    if len(contenu) > TAILLE_MAX_PHOTO_OCTETS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo trop volumineuse (max {TAILLE_MAX_PHOTO_OCTETS // (1024*1024)} Mo)",
        )

    devis = db.query(Devis).filter_by(id=parent.devis_id).first()
    if devis is None:
        # Devis cascade-deleted entre parent et retirage — improbable.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Devis parent introuvable",
        )

    nouvelle_tentative = parent.tentative_numero + 1
    cb = _executer_controle(
        db=db,
        user=user,
        devis=devis,
        bat_ref=bat_ref,
        photo_bytes=contenu,
        photo_mime=mime,
        sens_demande=sens_demande,
        tentative_numero=nouvelle_tentative,
        controle_bat_precedent_id=parent.id,
    )

    alerte_chef = nouvelle_tentative > TENTATIVES_SEUIL_ALERTE_CHEF
    return _to_analyse_response(cb, alerte_chef_atelier=alerte_chef)
