const API_URL = "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = `${response.status} ${body.detail}`;
    } catch {
      /* body non JSON */
    }
    throw new ApiError(
      response.status,
      `${init?.method ?? "GET"} ${path} → ${detail}`
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

// ---------------------------------------------------------------------------
// Entreprise (singleton)
// ---------------------------------------------------------------------------

export interface Entreprise {
  id: number;
  raison_sociale: string;
  siret: string;
  adresse: string | null;
  cp: string | null;
  ville: string | null;
  tel: string | null;
  email: string | null;
  pct_fg: number | null;
  pct_marge_defaut: number | null;
  heures_prod_presse_mois: number | null;
  heures_prod_finition_mois: number | null;
}

export type EntrepriseUpdate = Omit<Entreprise, "id">;

export const getEntreprise = () => apiFetch<Entreprise>("/api/entreprise");

export const updateEntreprise = (data: EntrepriseUpdate) =>
  apiFetch<Entreprise>("/api/entreprise", {
    method: "PUT",
    body: JSON.stringify(data),
  });

// ---------------------------------------------------------------------------
// Clients
// ---------------------------------------------------------------------------

export const SEGMENTS = [
  "alimentaire",
  "vin",
  "cosmetique",
  "biere",
  "alcool",
  "artisanat",
  "jardin",
] as const;
export type Segment = (typeof SEGMENTS)[number];

export interface Client {
  id: number;
  raison_sociale: string;
  siret: string | null;
  adresse_fact: string | null;
  cp_fact: string | null;
  ville_fact: string | null;
  contact: string | null;
  email: string | null;
  tel: string | null;
  segment: string | null;
  date_creation: string | null; // ISO YYYY-MM-DD
}

export type ClientCreate = Omit<Client, "id">;
export type ClientUpdate = Partial<ClientCreate>;

export const listClients = () =>
  apiFetch<Client[]>("/api/clients?limit=200");

export const getClient = (id: number) =>
  apiFetch<Client>(`/api/clients/${id}`);

export const createClient = (data: ClientCreate) =>
  apiFetch<Client>("/api/clients", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateClient = (id: number, data: ClientUpdate) =>
  apiFetch<Client>(`/api/clients/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteClient = (id: number) =>
  apiFetch<void>(`/api/clients/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Fournisseurs
// ---------------------------------------------------------------------------

export const CATEGORIES_FOURNISSEUR = [
  "complexe_adhesif",
  "encre_consommable",
] as const;
export type CategorieFournisseur = (typeof CATEGORIES_FOURNISSEUR)[number];

export interface Fournisseur {
  id: number;
  raison_sociale: string;
  categorie: string | null;
  contact: string | null;
  email: string | null;
  tel: string | null;
  conditions_paiement: string | null;
  delai_livraison_j: number | null;
}

export type FournisseurCreate = Omit<Fournisseur, "id">;
export type FournisseurUpdate = Partial<FournisseurCreate>;

export const listFournisseurs = () =>
  apiFetch<Fournisseur[]>("/api/fournisseurs?limit=200");

export const getFournisseur = (id: number) =>
  apiFetch<Fournisseur>(`/api/fournisseurs/${id}`);

export const createFournisseur = (data: FournisseurCreate) =>
  apiFetch<Fournisseur>("/api/fournisseurs", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateFournisseur = (id: number, data: FournisseurUpdate) =>
  apiFetch<Fournisseur>(`/api/fournisseurs/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteFournisseur = (id: number) =>
  apiFetch<void>(`/api/fournisseurs/${id}`, { method: "DELETE" });
