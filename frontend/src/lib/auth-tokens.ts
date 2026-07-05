// Source de vérité UNIQUE pour l'authentification côté client
// (consolidation audit 05/07/2026 — M6) : URL du backend, clés localStorage
// des tokens JWT, lecture/écriture, et refresh avec déduplication.
//
// Avant cette consolidation, API_URL était défini 7 fois et la logique de
// refresh existait en double (lib/api.ts + AuthContext.tsx). Tout module qui
// a besoin de l'URL backend ou des tokens importe désormais d'ici.
//
// URL du backend FastAPI.
// - En dev local : http://localhost:8000 (défaut)
// - En prod (Vercel) : NEXT_PUBLIC_API_URL définie dans les env vars Vercel,
//   pointant sur l'URL Railway du backend (ex: https://devis-flexo.up.railway.app)
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Sprint 12 Lot S12-E : clés localStorage des tokens (NE PAS renommer —
// les sessions existantes des utilisateurs en dépendent).
export const ACCESS_TOKEN_KEY = "devis_flexo_access_token";
export const REFRESH_TOKEN_KEY = "devis_flexo_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function doRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    const r = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!r.ok) return null;
    const tokens = await r.json();
    setTokens(tokens.access_token, tokens.refresh_token);
    return tokens.access_token as string;
  } catch {
    return null;
  }
}

// Déduplication de la promesse en vol : si N appels API prennent un 401
// simultanément, UN SEUL POST /api/auth/refresh part — les autres attendent
// la même promesse. Sans ça, le 2ᵉ refresh partait avec un refresh_token
// déjà consommé et échouait (déconnexion intempestive).
let refreshPromise: Promise<string | null> | null = null;

export function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}
