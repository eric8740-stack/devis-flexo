import { ApiError } from "@/lib/api";

// Client isolé pour le contrat REST `POST /api/optimisation/matcher-outil`
// (Sprint 14 Lot 2, backend implémenté en parallèle par CC #1).
// Toute évolution du contrat se reflète dans ce SEUL fichier — pas de
// fuite des types matcher dans le client API global.
//
// Mini-fetch local : pas de logique refresh JWT ici (transversal géré par
// `apiFetch` dans `lib/api.ts`). Si on tombe sur un 401, on remonte
// l'erreur — l'appel suivant via apiFetch principal déclenchera le refresh.

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ACCESS_TOKEN_KEY = "devis_flexo_access_token";

export interface MatcherOutilRequest {
  laize_etiquette_mm: number;
  dev_etiquette_mm: number;
  intervalle_dev_mm: number;
  intervalle_laize_mm: number;
  machine_id: number;
  nb_fronts_min?: number;
  nb_fronts_max?: number;
}

export interface MatcherOutilMatch {
  // null = match « nouvel outil à fabriquer sur mesure » (contrat backend
  // Lot 2 : si aucun cylindre du parc ne convient, le backend renvoie une
  // entrée unique avec cylindre_id=null + cout_outil_eur="200").
  cylindre_id: number | null;
  nb_dents: number;
  // Decimal sérialisé string (cohérent avec format_h_mm,
  // intervalle_dev_reel_mm, etc. dans api.ts). Conversion via
  // parseFloat / Number UNIQUEMENT à l'affichage.
  developpe_mm: string;
  nb_poses_dev: number;
  nb_poses_laize: number;
  nb_poses_total: number;
  cout_outil_eur: string;
  score_efficacite: number;
}

export interface MatcherOutilResponse {
  matches: MatcherOutilMatch[];
  nb_matches: number;
}

export async function postMatcherOutil(
  body: MatcherOutilRequest
): Promise<MatcherOutilResponse> {
  const path = "/api/optimisation/matcher-outil";
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
    // 422 = étiquette trop grande / aucun match faisable (contrat backend).
    throw new ApiError(response.status, `POST ${path} → ${detail}`);
  }

  return response.json();
}
