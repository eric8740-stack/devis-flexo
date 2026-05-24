import { ApiError } from "@/lib/api";

// Client isolé pour le module Contrôle BAT IA (FlexoCheck) — Sprint 15.
// Types alignés sur les schémas Pydantic de `backend/app/schemas/controle_bat.py`
// après rebase sur feat/s15-bat-ia-backend.
//
// Mini-fetch local, même convention que matcherOutil.ts (Sprint 14) :
// pas de logique refresh JWT ici (transversal géré par `apiFetch` dans
// `lib/api.ts`). Si on tombe sur un 401, on remonte l'erreur — l'appel
// suivant via apiFetch principal déclenchera le refresh.

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCESS_TOKEN_KEY = "devis_flexo_access_token";

function authHeader(): Record<string, string> {
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem(ACCESS_TOKEN_KEY)
      : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function throwApiError(
  response: Response,
  method: string,
  path: string,
): Promise<never> {
  let detail = `${response.status} ${response.statusText}`;
  try {
    const data = await response.json();
    if (data?.detail) detail = `${response.status} ${data.detail}`;
  } catch {
    /* corps non JSON */
  }
  throw new ApiError(response.status, `${method} ${path} → ${detail}`);
}

// ---------------------------------------------------------------------------
// Lot A — productions actives
// ---------------------------------------------------------------------------

// Aligné sur ProductionActiveItem (backend/app/schemas/controle_bat.py).
// Convention backend : `designation` reprend `Devis.numero` (DEV-YYYY-NNNN)
// tant qu'il n'y a pas de libellé business dédié. Toujours non-null.
export interface ProductionActive {
  devis_id: number;
  client: string | null;
  designation: string;
  machine: string;
  bat_reference_uploaded: boolean;
}

export interface ListProductionsActivesResponse {
  items: ProductionActive[];
  total: number;
}

export async function listProductionsActives(): Promise<ListProductionsActivesResponse> {
  const path = "/api/flexocheck/productions-actives";
  const response = await fetch(`${API_URL}${path}`, {
    method: "GET",
    headers: { "Content-Type": "application/json", ...authHeader() },
  });
  if (!response.ok) await throwApiError(response, "GET", path);
  return response.json();
}

// ---------------------------------------------------------------------------
// Lot B — Upload du BAT de référence
// ---------------------------------------------------------------------------

// Aligné sur BAT_MIME_TYPES_AUTORISES côté backend (PDF + JPEG/PNG/WebP).
export const BAT_MIME_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;

export type BatMimeType = (typeof BAT_MIME_TYPES)[number];

// Aligné sur TAILLE_MAX_BAT_OCTETS (10 Mo backend).
export const BAT_MAX_SIZE_MO = 10;

// Aligné sur BatUploadResponse. `bat_filename` peut être null (UploadFile
// sans nom d'origine).
export interface UploadBatResponse {
  devis_id: number;
  bat_filename: string | null;
  bat_mime_type: string;
  bat_uploaded_at: string;
}

export async function uploadBatReference(
  devisId: number,
  file: File,
): Promise<UploadBatResponse> {
  const path = "/api/flexocheck/controle-bat/upload-bat";
  // multipart/form-data : pas de `Content-Type` manuel, le navigateur ajoute
  // automatiquement le boundary. Forcer le header casse le parsing serveur.
  const formData = new FormData();
  formData.append("devis_id", String(devisId));
  formData.append("file", file);

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: authHeader(),
    body: formData,
  });
  if (!response.ok) await throwApiError(response, "POST", path);
  // 422 = devis introuvable, 415 = mime non supporté, 413 = > 10 Mo.
  return response.json();
}

// ---------------------------------------------------------------------------
// Lot C — Contexte de contrôle
// ---------------------------------------------------------------------------

// Aligné sur ControleBatContexte. `bat_url` / `bat_mime_type` sont None tant
// que l'opérateur n'a pas uploadé de BAT pour ce devis. `designation` est
// toujours présente (composée backend depuis Devis.numero).
//
// `bat_url` est un chemin RELATIF servi par GET /api/flexocheck/blobs/{key}
// (endpoint AUTHENTIFIÉ) — ne PAS le brancher directement en `<img src>`
// (pas de header JWT possible). Passer par `fetchControleBatBlob` qui
// renvoie un objectURL local consommable par img/iframe.
export interface ControleBatContext {
  devis_id: number;
  devis_numero: string;
  client_nom: string | null;
  designation: string;
  machine_nom: string;
  bat_url: string | null;
  bat_mime_type: string | null;
}

// Aligné sur PHOTO_TIRAGE_MIME_TYPES backend (JPEG/PNG/WebP, pas de GIF
// pour les photos atelier — Claude API multimodal n'aime pas).
export const PHOTO_TIRAGE_MIME_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;

export type PhotoTirageMimeType = (typeof PHOTO_TIRAGE_MIME_TYPES)[number];

// Aligné sur TAILLE_MAX_PHOTO_OCTETS (15 Mo backend).
export const PHOTO_TIRAGE_MAX_SIZE_MO = 15;

export async function getControleBatContext(
  devisId: number,
): Promise<ControleBatContext> {
  const path = `/api/flexocheck/controle-bat/contexte/${devisId}`;
  const response = await fetch(`${API_URL}${path}`, {
    method: "GET",
    headers: { "Content-Type": "application/json", ...authHeader() },
  });
  if (!response.ok) await throwApiError(response, "GET", path);
  return response.json();
}

// Fetch authentifié d'un blob (BAT ou photo de tirage) servi par
// `GET /api/flexocheck/blobs/{key}`. Le tag <img>/<iframe> ne peut pas
// envoyer de header JWT — d'où ce wrapper qui télécharge en blob puis
// crée un objectURL local consommable par les tags HTML.
//
// `blobUrl` est la valeur renvoyée par le backend (chemin RELATIF type
// `/api/flexocheck/blobs/{key}`). On préfixe avec API_URL si elle commence
// par `/`, sinon on assume une URL absolue (compat future Vercel Blob).
//
// L'appelant est responsable de `URL.revokeObjectURL(returnedUrl)` au
// unmount pour éviter les fuites mémoire.
export async function fetchControleBatBlob(blobUrl: string): Promise<string> {
  const target = blobUrl.startsWith("/") ? `${API_URL}${blobUrl}` : blobUrl;
  const response = await fetch(target, { headers: authHeader() });
  if (!response.ok) {
    throw new ApiError(
      response.status,
      `GET ${blobUrl} → ${response.status} ${response.statusText}`,
    );
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

// ---------------------------------------------------------------------------
// Résultat d'analyse — aligné sur ControleBatAnalyseResponse
// ---------------------------------------------------------------------------

// Aligné sur DecisionRecommandee backend. À noter `"ajuster_avant_demarrage"`
// au lieu du raccourci `"ajuster"` qu'on avait avant rebase.
export type DecisionRecommandee =
  | "valider"
  | "ajuster_avant_demarrage"
  | "rejeter";

export type NiveauConfiance = "haut" | "moyen" | "faible";

// Aligné sur EcartDetail backend (extra="allow" côté Pydantic mais on
// expose le contrat minimum côté UI).
export interface EcartDetail {
  type: string;
  gravite: string;
  localisation: string | null;
  description: string | null;
  suggestion_correction: string | null;
}

// Gravités attendues côté affichage. Le backend laisse passer en str pour
// rester souple (autres labels possibles côté IA), mais l'UI ne dégrade
// gracieusement que sur ces 3 valeurs ; les autres tombent dans le bucket
// par défaut.
export type GraviteEcart = "critique" | "majeur" | "mineur";

// Sens d'enroulement normalisé flexo (ANSI/AWA SE1-SE8).
export type SensEnroulement =
  | "SE1"
  | "SE2"
  | "SE3"
  | "SE4"
  | "SE5"
  | "SE6"
  | "SE7"
  | "SE8";

// Codes d'action correction sens (alignés sur ActionCorrectionSens backend).
export type ActionCorrectionSens =
  | "inversion_cliche"
  | "ajustement_rebobineuse"
  | "confirmation_client";

// Aligné sur OptionCorrectionSens backend. Sprint 15 Lot 4 : `recommandee`
// = true sur l'option auto-sélectionnée par le diagnostic coherence_sens
// → l'UI met cette option en avant (couleur, ordre).
export interface OptionCorrectionSensItem {
  code: ActionCorrectionSens;
  libelle: string;
  description: string;
  recommandee: boolean;
}

export interface AlerteSensEnroulement {
  message: string;
  options_correction: OptionCorrectionSensItem[];
}

// Aligné sur ControleBatAnalyseResponse. Note : score_conformite est un
// Decimal côté Pydantic, sérialisé en string par défaut (cf. matcher-outil
// developpe_mm / cout_outil_eur). Convention projet : on parse via
// parseFloat UNIQUEMENT à l'affichage.
export interface ControleBatResult {
  controle_id: number;
  devis_id: number;
  tentative: number;
  score_conformite: string | null;
  decision_recommandee: DecisionRecommandee | null;
  niveau_confiance: NiveauConfiance | null;
  // Listes toujours présentes (vide si rien) — pas optionnel côté backend.
  limites_analyse: string[];
  ecarts: EcartDetail[];
  elements_conformes: string[];
  elements_manquants: string[];
  sens_enroulement_detecte: string | null;
  sens_enroulement_demande: string | null;
  alerte_sens_enroulement: AlerteSensEnroulement | null;
  // Renvoyé uniquement par /retirage (true si tentative_numero > 3,
  // null pour le contrôle initial). Cf. brief Lot 3 § endpoint 7.
  alerte_chef_atelier: boolean | null;
}

export async function createControleBat(
  devisId: number,
  photo: File,
): Promise<ControleBatResult> {
  const path = "/api/flexocheck/controle-bat/";
  const formData = new FormData();
  formData.append("devis_id", String(devisId));
  formData.append("photo", photo);

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: authHeader(),
    body: formData,
  });
  if (!response.ok) await throwApiError(response, "POST", path);
  // 404 = devis inexistant, 409 = BAT non rattaché, 413 = photo > 15 Mo,
  // 422 = mime non supporté, 503 = service IA indisponible.
  return response.json();
}

// ---------------------------------------------------------------------------
// Lot E — Décision finale opérateur + workflow re-tirage
// ---------------------------------------------------------------------------

// Aligné sur DecisionFinale backend. "en_attente" est l'état initial créé
// par le backend ; l'opérateur ne le renvoie jamais (cf. DecisionFinaleIn).
export type DecisionFinale =
  | "en_attente"
  | "valide"
  | "valide_avec_reserves"
  | "rejete";

// Aligné sur DecisionFinaleIn (entrée POST decision). "en_attente" exclu —
// seuls les 3 verdicts opérateur sont acceptés.
export type DecisionFinaleInput =
  | "valide"
  | "valide_avec_reserves"
  | "rejete";

export interface DecideControleRequest {
  decision_finale: DecisionFinaleInput;
  decideur: string;
  // Renommé `motif` → `motif_decision` pour aligner sur le schema backend.
  motif_decision?: string;
}

// Aligné sur ControleBatDetail (retour POST decision). Beaucoup de champs
// dérivés du modèle SQL. On expose le minimum utile à l'UI Lot E (affichage
// du bloc "décision enregistrée") — le reste est consommable si besoin.
export interface DecideControleResponse {
  id: number;
  entreprise_id: number;
  devis_id: number;
  decision_finale: DecisionFinale;
  decideur: string;
  motif_decision: string | null;
  tentative_numero: number;
  controle_bat_precedent_id: number | null;
  created_at: string;
}

export async function decideControleBat(
  controleId: number,
  body: DecideControleRequest,
): Promise<DecideControleResponse> {
  const path = `/api/flexocheck/controle-bat/${controleId}/decision`;
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  });
  if (!response.ok) await throwApiError(response, "POST", path);
  return response.json();
}

// Le backend chaîne via `controle_bat_precedent_id = parent.id` et calcule
// `tentative_numero = parent.tentative_numero + 1`. Conséquence : on doit
// chaîner depuis la DERNIÈRE tentative (`lastResult.controle_id`), pas
// depuis la première — sinon `tentative_numero` stagne à 2 indéfiniment.
export async function relancerTirage(
  controleId: number,
  photo: File,
): Promise<ControleBatResult> {
  const path = `/api/flexocheck/controle-bat/${controleId}/retirage`;
  const formData = new FormData();
  formData.append("photo", photo);

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: authHeader(),
    body: formData,
  });
  if (!response.ok) await throwApiError(response, "POST", path);
  // 404 = parent inexistant, 409 = BAT supprimé entre temps, 413 = photo
  // > 15 Mo, 422 = mime non supporté, 503 = service IA indisponible.
  return response.json();
}
