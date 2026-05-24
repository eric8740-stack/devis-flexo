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

// Gravité d'un écart de conformité. Ordre métier : critique > majeur > mineur
// — utilisé pour le tri et la couleur côté UI.
export type GraviteEcart = "critique" | "majeur" | "mineur";

// Sens d'enroulement normalisé flexo (ANSI/AWA SE1-SE8). null si le backend
// n'a pas pu déterminer le sens (ex: photo trop floue).
export type SensEnroulement =
  | "SE1"
  | "SE2"
  | "SE3"
  | "SE4"
  | "SE5"
  | "SE6"
  | "SE7"
  | "SE8";

export type DecisionRecommandee = "valider" | "ajuster" | "rejeter";

export type NiveauConfiance = "haut" | "moyen" | "faible";

export interface EcartConformite {
  gravite: GraviteEcart;
  localisation: string;
  description: string;
  suggestion_correction: string | null;
}

// Si l'analyse détecte une divergence entre sens demandé et sens vu sur la
// photo, on déclenche un bandeau bloquant côté UI. Les `options_correction`
// sont les 3 chemins de remédiation décidés métier (cf. brief Lot D).
export interface AlerteSensEnroulement {
  message: string;
  options_correction: Array<{
    code:
      | "inversion_cliche"
      | "ajustement_rebobineuse"
      | "confirmation_client";
    libelle: string;
    description: string;
  }>;
}

// Réponse complète du POST /api/flexocheck/controle-bat/.
// Lot C utilise un sous-ensemble minimal (controle_id, tentative) ; Lot D
// consomme la totalité pour l'affichage opérateur. Les champs métier
// (score, écarts, sens) restent optionnels au niveau du type pour rester
// tolérant aux analyses partielles côté backend (ex: photo illisible ⇒
// pas d'écarts mais on renvoie quand même un controle_id + niveau_confiance
// "faible" + limites_analyse).
export interface ControleBatResult {
  controle_id: number;
  devis_id: number;
  tentative: number;
  score_conformite?: number;
  decision_recommandee?: DecisionRecommandee;
  niveau_confiance?: NiveauConfiance;
  limites_analyse?: string[];
  ecarts?: EcartConformite[];
  elements_conformes?: string[];
  elements_manquants?: string[];
  sens_enroulement_detecte?: SensEnroulement | null;
  sens_enroulement_demande?: SensEnroulement | null;
  alerte_sens_enroulement?: AlerteSensEnroulement | null;
  // Lot E — backend lève ce flag au-delà de N tentatives échouées (seuil
  // métier 3 d'après le brief, mais le seuil reste côté backend pour
  // pouvoir évoluer). L'UI affiche un bandeau "Prévenir le chef d'atelier".
  alerte_chef_atelier?: boolean;
}

// ---------------------------------------------------------------------------
// Lot E — Décision finale opérateur + workflow re-tirage
// ---------------------------------------------------------------------------

export type DecisionFinale = "valider" | "rejeter";

export interface DecideControleRequest {
  decision_finale: DecisionFinale;
  decideur: string;
  motif?: string;
}

export interface DecideControleResponse {
  controle_id: number;
  devis_id: number;
  decision_finale: DecisionFinale;
  decideur: string;
  motif: string | null;
  decided_at: string;
}

export async function decideControleBat(
  controleId: number,
  body: DecideControleRequest,
): Promise<DecideControleResponse> {
  const path = `/api/flexocheck/controle-bat/${controleId}/decision`;
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
      : null;

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (data?.detail) detail = `${response.status} ${data.detail}`;
    } catch {
      /* corps non JSON */
    }
    // 404 = controle introuvable, 409 = décision déjà enregistrée (idempotent
    // côté UI : on remonte l'erreur, l'utilisateur recharge).
    throw new ApiError(response.status, `POST ${path} → ${detail}`);
  }

  return response.json();
}

export async function relancerTirage(
  controleId: number,
  photo: File,
): Promise<ControleBatResult> {
  const path = `/api/flexocheck/controle-bat/${controleId}/retirage`;
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
      : null;

  const formData = new FormData();
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
    // 409 = contrôle déjà décidé (plus de retirage possible), 413 = photo
    // trop grosse, 422 = photo invalide, 503 = service IA indisponible.
    throw new ApiError(response.status, `POST ${path} → ${detail}`);
  }

  return response.json();
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
