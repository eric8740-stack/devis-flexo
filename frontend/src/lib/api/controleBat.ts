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
