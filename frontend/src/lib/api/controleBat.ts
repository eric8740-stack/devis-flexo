import { ApiError } from "@/lib/api";

// Client isolé pour le module Contrôle BAT IA (FlexoCheck) — Sprint 15.
// Backend implémenté en parallèle par CC #1 ; tant que les endpoints ne sont
// pas mergés, les types ci-dessous sont une PROJECTION des schémas Pydantic
// attendus, à ré-aligner au rebase sur `feat/s15-bat-ia-backend`.
//
// Mini-fetch local, même convention que matcherOutil.ts (Sprint 14) :
// pas de logique refresh JWT ici (transversal géré par `apiFetch` dans
// `lib/api.ts`). Si on tombe sur un 401, on remonte l'erreur — l'appel
// suivant via apiFetch principal déclenchera le refresh.

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCESS_TOKEN_KEY = "devis_flexo_access_token";

// ---------------------------------------------------------------------------
// Lot A — productions actives
// ---------------------------------------------------------------------------

// Production en cours = devis confirmé dont la fabrication n'est pas terminée.
// Le concept "production active" ne correspond PAS au DevisStatut existant
// (`brouillon` | `valide`) ; CC #1 ajoute l'état "en_production" côté backend
// + le filtre dédié. Pour le Lot A on consomme la projection minimale
// nécessaire à l'écran atelier : identification devis, client, désignation,
// machine.
export interface ProductionActive {
  devis_id: number;
  devis_numero: string;
  client_nom: string | null;
  designation: string | null;
  machine_id: number;
  machine_nom: string;
  // Indicateur du BAT de référence rattaché (Lot B) — l'opérateur ne peut
  // déclencher un contrôle (Lot C) que si bat_reference_uploaded=true.
  bat_reference_uploaded: boolean;
}

export interface ListProductionsActivesResponse {
  items: ProductionActive[];
  total: number;
}

export async function listProductionsActives(): Promise<ListProductionsActivesResponse> {
  const path = "/api/flexocheck/productions-actives";
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
      : null;

  const response = await fetch(`${API_URL}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (data?.detail) detail = `${response.status} ${data.detail}`;
    } catch {
      /* corps non JSON */
    }
    // 403 attendu si l'utilisateur n'a pas `has_flexocheck` côté backend.
    throw new ApiError(response.status, `GET ${path} → ${detail}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Lot B — Upload du BAT de référence
// ---------------------------------------------------------------------------

// Formats autorisés pour le BAT de référence : PDF (typique export imprimeur)
// + images haute déf (cas où le client renvoie une photo annotée). Aligné sur
// l'analyse photo S13 + tolérance PDF.
export const BAT_MIME_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;

export type BatMimeType = (typeof BAT_MIME_TYPES)[number];

// Taille max alignée sur l'analyse photo S13. Un BAT PDF imprimeur tient
// presque toujours en <10 Mo ; au-delà on demande compression côté client.
export const BAT_MAX_SIZE_MO = 10;

export interface UploadBatResponse {
  devis_id: number;
  bat_filename: string;
  bat_mime_type: string;
  bat_uploaded_at: string;
}

export async function uploadBatReference(
  devisId: number,
  file: File,
): Promise<UploadBatResponse> {
  const path = "/api/flexocheck/controle-bat/upload-bat";
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
      : null;

  // multipart/form-data : pas de `Content-Type` manuel, le navigateur ajoute
  // automatiquement le boundary. Forcer le header casse le parsing serveur.
  const formData = new FormData();
  formData.append("devis_id", String(devisId));
  formData.append("file", file);

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (data?.detail) detail = `${response.status} ${data.detail}`;
    } catch {
      /* corps non JSON */
    }
    // 413 = fichier trop gros, 415 = type non supporté, 422 = devis introuvable.
    throw new ApiError(response.status, `POST ${path} → ${detail}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Lot C — Contexte de contrôle + création d'un contrôle (capture 1er tirage)
// ---------------------------------------------------------------------------

// Projection minimale du contexte de contrôle nécessaire à l'écran détail :
// identification devis + URL du BAT à afficher. Le shape complet (sens
// enroulement attendu, palette couleurs, etc.) viendra avec les schémas
// Pydantic de CC #1 et sera consommé par le Lot D pour comparer.
export interface ControleBatContext {
  devis_id: number;
  devis_numero: string;
  client_nom: string | null;
  designation: string | null;
  machine_nom: string;
  // URL servant le BAT de référence — supposée signée (S3 presigned ou
  // équivalent) pour pouvoir être consommée par <img>/<iframe> sans header
  // d'auth. Si CC #1 expose un endpoint auth-required à la place, on
  // adaptera côté UI (pattern IAPhotoAuthenticated).
  bat_url: string;
  bat_mime_type: string;
}

// Format max pour la photo du 1er tirage : ~15 Mo (photo tablette ≈ 4-8 Mo,
// on prévoit un peu de marge pour les capteurs récents). Plus permissif
// que le BAT car la capture peut produire des fichiers HEIC convertis ou
// des JPEG haute déf.
export const PHOTO_TIRAGE_MAX_SIZE_MO = 15;

// Réponse minimale du POST /api/flexocheck/controle-bat/. Lot C n'a besoin
// que de savoir « l'analyse est revenue, voici l'id ». Le Lot D enrichira
// avec score, écarts, alerte sens enroulement, etc.
export interface ControleBatResult {
  controle_id: number;
  devis_id: number;
  tentative: number;
  // Champs Lot D (optionnels ici pour ne pas pré-empter le contrat) :
  score_conformite?: number;
  decision_recommandee?: "valider" | "ajuster" | "rejeter";
}

export async function getControleBatContext(
  devisId: number,
): Promise<ControleBatContext> {
  const path = `/api/flexocheck/controle-bat/contexte/${devisId}`;
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
      : null;

  const response = await fetch(`${API_URL}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (data?.detail) detail = `${response.status} ${data.detail}`;
    } catch {
      /* corps non JSON */
    }
    // 404 = devis inexistant, 409 = BAT non rattaché (contrôle impossible).
    throw new ApiError(response.status, `GET ${path} → ${detail}`);
  }

  return response.json();
}

export async function createControleBat(
  devisId: number,
  photo: File,
): Promise<ControleBatResult> {
  const path = "/api/flexocheck/controle-bat/";
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
      : null;

  const formData = new FormData();
  formData.append("devis_id", String(devisId));
  formData.append("photo", photo);

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (data?.detail) detail = `${response.status} ${data.detail}`;
    } catch {
      /* corps non JSON */
    }
    // 409 = BAT non rattaché, 413 = photo trop grosse, 422 = devis ou
    // photo invalide, 503 = service IA indisponible.
    throw new ApiError(response.status, `POST ${path} → ${detail}`);
  }

  return response.json();
}
