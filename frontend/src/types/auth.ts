// Types frontend correspondant aux schémas Pydantic backend (Sprint 12).
// User côté API auth = champs renvoyés par GET /api/auth/me (UserMe).

export interface User {
  id: number;
  email: string;
  nom_contact: string;
  entreprise_id: number;
  nom_entreprise: string;
  is_admin: boolean;
  is_active: boolean;
  date_creation: string;
  date_derniere_connexion: string | null;
  // Sprint 15 — flag d'accès au module FlexoCheck (Contrôle BAT IA).
  // Optionnel : absent côté backend tant que CC #1 n'a pas exposé le champ,
  // alors traité comme `false` (cf. helper `hasFlexocheck` côté UI).
  has_flexocheck?: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  nom_entreprise: string;
  nom_contact: string;
}
