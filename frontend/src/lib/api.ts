import type { AdminUser, AdminUserCreate } from "@/types/admin";

// URL du backend FastAPI.
// - En dev local : http://localhost:8000 (défaut)
// - En prod (Vercel) : NEXT_PUBLIC_API_URL définie dans les env vars Vercel,
//   pointant sur l'URL Railway du backend (ex: https://devis-flexo.up.railway.app)
const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Sprint 12 Lot S12-E : intercepteur Bearer JWT + refresh auto sur 401.
const ACCESS_TOKEN_KEY = "devis_flexo_access_token";
const REFRESH_TOKEN_KEY = "devis_flexo_refresh_token";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function readToken(key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}

function clearTokensAndRedirect() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  // Hard redirect plutôt que router.push : on est hors d'un composant React
  // ici, et on veut couper tout state en cours (cache RSC, fetch en vol).
  window.location.href = "/login";
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = readToken(REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;
  try {
    const r = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!r.ok) return null;
    const tokens = await r.json();
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    }
    return tokens.access_token as string;
  } catch {
    return null;
  }
}

function buildHeaders(
  init: RequestInit | undefined,
  token: string | null
): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers ?? {}),
  };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_URL}${path}`;
  const initialToken = readToken(ACCESS_TOKEN_KEY);

  let response = await fetch(url, {
    ...init,
    headers: buildHeaders(init, initialToken),
  });

  // 401 + token présent → tente UN refresh, puis retry l'appel d'origine.
  // Si le refresh échoue, on clear et redirige vers /login.
  if (response.status === 401 && initialToken) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      response = await fetch(url, {
        ...init,
        headers: buildHeaders(init, newToken),
      });
    } else {
      clearTokensAndRedirect();
    }
  }

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
// Sprint 0-1 : Entreprise (singleton)
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
  // PR #9.1 — paramètres BAT (renvoyés en string par FastAPI car Decimal)
  chute_laterale_min_mm: string;
  palier_laize_papier_mm: number;
  refilage_systematique: boolean;
  marge_liner_mm: string;
}

export type EntrepriseUpdate = Omit<Entreprise, "id">;

export const getEntreprise = () => apiFetch<Entreprise>("/api/entreprise");

export const updateEntreprise = (data: EntrepriseUpdate) =>
  apiFetch<Entreprise>("/api/entreprise", {
    method: "PUT",
    body: JSON.stringify(data),
  });

// ---------------------------------------------------------------------------
// Sprint 0-1 : Clients
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
  date_creation: string | null;
}

export type ClientCreate = Omit<Client, "id">;
export type ClientUpdate = Partial<ClientCreate>;

export const listClients = () => apiFetch<Client[]>("/api/clients?limit=200");
export const getClient = (id: number) => apiFetch<Client>(`/api/clients/${id}`);
export const createClient = (data: ClientCreate) =>
  apiFetch<Client>("/api/clients", { method: "POST", body: JSON.stringify(data) });
export const updateClient = (id: number, data: ClientUpdate) =>
  apiFetch<Client>(`/api/clients/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteClient = (id: number) =>
  apiFetch<void>(`/api/clients/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Sprint 0-1 : Fournisseurs
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

// ---------------------------------------------------------------------------
// Sprint 2 : Machine (presses flexo)
// ---------------------------------------------------------------------------

// Sprint 9 v2 Lot 9d : refactor statut String → actif Boolean uniformisé.
// Mini-fix vitesse-machine 05/05/2026 : exposition des 3 champs jusque-là
// invisibles côté frontend mais utilisés par le moteur de coût
// (vitesse_moyenne_m_h pour P5+P7, duree_calage_h pour P7,
//  laize_max_mm NOT NULL pour matching cylindres).
export interface Machine {
  id: number;
  nom: string;
  largeur_max_mm: number | null;
  // Numeric(6,2) NOT NULL côté backend — required à la création.
  laize_max_mm: number;
  // Catalogue constructeur (m/min) — n'impacte PAS le calcul. Indicatif.
  vitesse_max_m_min: number | null;
  // Vitesse réaliste de production en m/h (= m/min × 60). Pilote
  // réellement P5 Roulage et P7 MO. UI saisit en m/min ; conversion ×60
  // transparente vers ce champ pour stockage BDD.
  vitesse_moyenne_m_h: number | null;
  // Durée calage en h (Numeric(4,2)). Pilote l'heures_calage de P7 MO.
  duree_calage_h: number | null;
  nb_couleurs: number | null;
  cout_horaire_eur: number | null;
  actif: boolean;
  commentaire: string | null;
  date_creation: string;
  date_maj: string;
}

export type MachineCreate = Omit<Machine, "id" | "date_creation" | "date_maj">;
export type MachineUpdate = Partial<MachineCreate>;

export const listMachines = (includeInactives = false) =>
  apiFetch<Machine[]>(
    `/api/machines?limit=200${includeInactives ? "&include_inactives=true" : ""}`
  );
export const getMachine = (id: number) => apiFetch<Machine>(`/api/machines/${id}`);
export const createMachine = (data: MachineCreate) =>
  apiFetch<Machine>("/api/machines", { method: "POST", body: JSON.stringify(data) });
export const updateMachine = (id: number, data: MachineUpdate) =>
  apiFetch<Machine>(`/api/machines/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteMachine = (id: number) =>
  apiFetch<void>(`/api/machines/${id}`, { method: "DELETE" });
export const reactiverMachine = (id: number) =>
  apiFetch<Machine>(`/api/machines/${id}/reactiver`, { method: "POST" });

// ---------------------------------------------------------------------------
// Sprint 2 : OperationFinition
// ---------------------------------------------------------------------------

export const UNITES_FACTURATION = ["m2", "ml", "unite", "millier"] as const;
export type UniteFacturation = (typeof UNITES_FACTURATION)[number];
export const STATUTS_OPERATION = ["actif", "inactif"] as const;
export type StatutOperation = (typeof STATUTS_OPERATION)[number];

export interface OperationFinition {
  id: number;
  nom: string;
  unite_facturation: UniteFacturation;
  cout_unitaire_eur: number | null;
  temps_minutes_unite: number | null;
  statut: StatutOperation;
  commentaire: string | null;
  date_creation: string;
  date_maj: string;
}

export type OperationFinitionCreate = Omit<
  OperationFinition,
  "id" | "date_creation" | "date_maj"
>;
export type OperationFinitionUpdate = Partial<OperationFinitionCreate>;

export const listOperationsFinition = () =>
  apiFetch<OperationFinition[]>("/api/operations-finition?limit=200");
export const getOperationFinition = (id: number) =>
  apiFetch<OperationFinition>(`/api/operations-finition/${id}`);
export const createOperationFinition = (data: OperationFinitionCreate) =>
  apiFetch<OperationFinition>("/api/operations-finition", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateOperationFinition = (id: number, data: OperationFinitionUpdate) =>
  apiFetch<OperationFinition>(`/api/operations-finition/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteOperationFinition = (id: number) =>
  apiFetch<void>(`/api/operations-finition/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Sprint 2 : PartenaireST (sous-traitants finition)
// ---------------------------------------------------------------------------

export const PRESTATION_TYPES = ["finition", "decoupe", "dorure", "autre"] as const;
export type PrestationType = (typeof PRESTATION_TYPES)[number];
// Sprint 9 v2 Lot 9d : refactor statut → actif Boolean
export interface PartenaireST {
  id: number;
  raison_sociale: string;
  siret: string | null;
  contact_nom: string | null;
  contact_email: string | null;
  contact_tel: string | null;
  prestation_type: PrestationType | null;
  delai_jours_moyen: number | null;
  qualite_score: number | null;
  commentaire: string | null;
  actif: boolean;
  date_creation: string;
  date_maj: string;
}

export type PartenaireSTCreate = Omit<
  PartenaireST,
  "id" | "date_creation" | "date_maj"
>;
export type PartenaireSTUpdate = Partial<PartenaireSTCreate>;

export const listPartenairesST = (includeInactives = false) =>
  apiFetch<PartenaireST[]>(
    `/api/partenaires-st?limit=200${includeInactives ? "&include_inactives=true" : ""}`
  );
export const getPartenaireST = (id: number) =>
  apiFetch<PartenaireST>(`/api/partenaires-st/${id}`);
export const createPartenaireST = (data: PartenaireSTCreate) =>
  apiFetch<PartenaireST>("/api/partenaires-st", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updatePartenaireST = (id: number, data: PartenaireSTUpdate) =>
  apiFetch<PartenaireST>(`/api/partenaires-st/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deletePartenaireST = (id: number) =>
  apiFetch<void>(`/api/partenaires-st/${id}`, { method: "DELETE" });
export const reactiverPartenaireST = (id: number) =>
  apiFetch<PartenaireST>(`/api/partenaires-st/${id}/reactiver`, {
    method: "POST",
  });

// ---------------------------------------------------------------------------
// Sprint 2 : ChargeMensuelle (frais fixes)
// ---------------------------------------------------------------------------

export const CATEGORIES_CHARGE = [
  "loyer",
  "salaires",
  "energie",
  "assurance",
  "fournitures",
  "autre",
] as const;
export type CategorieCharge = (typeof CATEGORIES_CHARGE)[number];

export interface ChargeMensuelle {
  id: number;
  libelle: string;
  categorie: CategorieCharge;
  montant_eur: number;
  date_debut: string;
  date_fin: string | null;
  commentaire: string | null;
  date_creation: string;
  date_maj: string;
}

export type ChargeMensuelleCreate = Omit<
  ChargeMensuelle,
  "id" | "date_creation" | "date_maj"
>;
export type ChargeMensuelleUpdate = Partial<ChargeMensuelleCreate>;

export const listChargesMensuelles = () =>
  apiFetch<ChargeMensuelle[]>("/api/charges-mensuelles?limit=200");
export const getChargeMensuelle = (id: number) =>
  apiFetch<ChargeMensuelle>(`/api/charges-mensuelles/${id}`);
export const createChargeMensuelle = (data: ChargeMensuelleCreate) =>
  apiFetch<ChargeMensuelle>("/api/charges-mensuelles", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateChargeMensuelle = (id: number, data: ChargeMensuelleUpdate) =>
  apiFetch<ChargeMensuelle>(`/api/charges-mensuelles/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteChargeMensuelle = (id: number) =>
  apiFetch<void>(`/api/charges-mensuelles/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Sprint 2 : Complexe (matières adhésives — prix_m2_eur CRITIQUE pour S3)
// ---------------------------------------------------------------------------

export const FAMILLES_COMPLEXE = [
  "bopp",
  "pp",
  "pe",
  "pvc_vinyle",
  "thermique",
  "papier_couche",
  "papier_standard",
  "papier_epais",
  "papier_kraft",
  "papier_verge",
] as const;
export type FamilleComplexe = (typeof FAMILLES_COMPLEXE)[number];
// Sprint 9 v2 Lot 9d : refactor statut → actif Boolean
export interface Complexe {
  id: number;
  reference: string;
  famille: FamilleComplexe;
  face_matiere: string | null;
  grammage_g_m2: number | null;
  adhesif_type: string | null;
  prix_m2_eur: number;
  fournisseur_id: number | null;
  actif: boolean;
  commentaire: string | null;
  date_creation: string;
  date_maj: string;
}

export type ComplexeCreate = Omit<Complexe, "id" | "date_creation" | "date_maj">;
export type ComplexeUpdate = Partial<ComplexeCreate>;

export const listComplexes = (includeInactives = false) =>
  apiFetch<Complexe[]>(
    `/api/complexes?limit=200${includeInactives ? "&include_inactives=true" : ""}`
  );
export const getComplexe = (id: number) =>
  apiFetch<Complexe>(`/api/complexes/${id}`);
export const createComplexe = (data: ComplexeCreate) =>
  apiFetch<Complexe>("/api/complexes", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateComplexe = (id: number, data: ComplexeUpdate) =>
  apiFetch<Complexe>(`/api/complexes/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteComplexe = (id: number) =>
  apiFetch<void>(`/api/complexes/${id}`, { method: "DELETE" });
export const reactiverComplexe = (id: number) =>
  apiFetch<Complexe>(`/api/complexes/${id}/reactiver`, { method: "POST" });

// ---------------------------------------------------------------------------
// Sprint 2 : Catalogue (produits récurrents par client)
// ---------------------------------------------------------------------------

export const FREQUENCES_ESTIMEES = [
  "ponctuelle",
  "mensuelle",
  "trimestrielle",
  "annuelle",
] as const;
export type FrequenceEstimee = (typeof FREQUENCES_ESTIMEES)[number];
export const STATUTS_CATALOGUE = ["actif", "archive"] as const;
export type StatutCatalogue = (typeof STATUTS_CATALOGUE)[number];

export interface CatalogueItem {
  id: number;
  code_produit: string;
  designation: string;
  client_id: number;
  machine_id: number | null;
  matiere: string | null;
  format_mm: string | null;
  nb_couleurs: number | null;
  prix_unitaire_eur: number | null;
  frequence_estimee: FrequenceEstimee | null;
  commentaire: string | null;
  statut: StatutCatalogue;
  date_creation: string;
  date_maj: string;
}

export type CatalogueCreate = Omit<
  CatalogueItem,
  "id" | "date_creation" | "date_maj"
>;
export type CatalogueUpdate = Partial<CatalogueCreate>;

export const listCatalogue = (clientId?: number) => {
  const qs = clientId ? `?limit=200&client_id=${clientId}` : "?limit=200";
  return apiFetch<CatalogueItem[]>(`/api/catalogue${qs}`);
};
export const getCatalogueItem = (id: number) =>
  apiFetch<CatalogueItem>(`/api/catalogue/${id}`);
export const createCatalogueItem = (data: CatalogueCreate) =>
  apiFetch<CatalogueItem>("/api/catalogue", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateCatalogueItem = (id: number, data: CatalogueUpdate) =>
  apiFetch<CatalogueItem>(`/api/catalogue/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteCatalogueItem = (id: number) =>
  apiFetch<void>(`/api/catalogue/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Sprint 3 Lot 3g : Cost engine v2 — POST /api/cost/calculer
// ---------------------------------------------------------------------------

export const ENCRES_TYPES = [
  "process_cmj",
  "process_black_hc",
  "pantone",
  "blanc_high_opaque",
  "metallise",
] as const;
export type EncreType = (typeof ENCRES_TYPES)[number];

// Libellés humains pour l'UI (clés tarif_encre.type_encre côté backend).
export const ENCRES_LIBELLES: Record<EncreType, string> = {
  process_cmj: "Process CMJN",
  process_black_hc: "Black High Coverage",
  pantone: "Pantone",
  blanc_high_opaque: "Blanc High Opacity",
  metallise: "Métallisée",
};

export interface PartenaireSTForfait {
  partenaire_st_id: number;
  // Decimal côté backend → string en JSON pour préserver la précision.
  montant_eur: string;
}

// Sprint 7 Lot 7b — mode_calcul (manuel = Sprint 5 / matching = nouveau S7)
export type ModeCalcul = "manuel" | "matching";

export interface DevisInput {
  complexe_id: number;
  laize_utile_mm: number;
  ml_total: number;
  nb_couleurs_par_type: Record<string, number>;
  machine_id: number;
  // Sprint 5 Lot 5b — format / outillage / découpe (defaults backend Option B)
  format_etiquette_largeur_mm?: number;
  format_etiquette_hauteur_mm?: number;
  nb_poses_largeur?: number;
  nb_poses_developpement?: number;
  forme_speciale?: boolean;
  outil_decoupe_existant?: boolean;
  outil_decoupe_id?: number | null;
  nb_traces_complexite?: number;
  // Sprint 7 Lot 7b — mode + intervalle conditionnel
  mode_calcul?: ModeCalcul;
  intervalle_mm?: string | null; // Decimal backend → string ; null en matching
  // Sous-traitance + overrides
  forfaits_st: PartenaireSTForfait[];
  heures_dossier_override?: string | null;
  pct_marge_override?: string | null;
}

export interface PosteResult {
  poste_numero: number;
  libelle: string;
  // Decimal côté backend → string en JSON.
  montant_eur: string;
  // dict[str, float | int | str | None] côté backend.
  // null autorisé (ex. outil_decoupe_id non identifié, Lot 5c).
  details: Record<string, string | number | null>;
}

export interface DevisOutput {
  // Sprint 7 Lot 7c V2 — discriminant pour Union avec DevisOutputMatching
  mode: "manuel";
  postes: PosteResult[];
  cout_revient_eur: string;
  pct_marge_appliquee: string;
  prix_vente_ht_eur: string;
  // Sprint 5 Lot 5c — livrable commercial clé (Note 9 mémoire).
  prix_au_mille_eur: string;
}

// Sprint 7 Lot 7c V2 — sortie multi-résultats mode 'matching'
export interface CandidatCylindreOutput {
  z: number; // 51-144
  nb_etiq_par_tour: number; // 1-40
  circonference_mm: string; // Decimal
  pas_mm: string;
  intervalle_mm: string;
  nb_etiq_par_metre: number;
  // Devis calculé pour ce candidat (HT identique entre candidats — postes
  // ne dépendent pas du cylindre dans le moteur actuel)
  postes: PosteResult[];
  cout_revient_eur: string;
  pct_marge_appliquee: string;
  prix_vente_ht_eur: string;
  prix_au_mille_eur: string;
}

export interface DevisOutputMatching {
  mode: "matching";
  candidats: CandidatCylindreOutput[]; // 1-3 entrées
}

// Union discriminée par `mode` — TypeScript narrowing automatique sur data.mode
export type DevisCalculResult = DevisOutput | DevisOutputMatching;

export const calculerDevis = (input: DevisInput) =>
  apiFetch<DevisCalculResult>("/api/cost/calculer", {
    method: "POST",
    body: JSON.stringify(input),
  });

// ---------------------------------------------------------------------------
// Sprint 5 Lot 5b : Catalogue outils de découpe
// ---------------------------------------------------------------------------

export interface OutilDecoupeRead {
  id: number;
  libelle: string;
  format_l_mm: number;
  format_h_mm: number;
  nb_poses_l: number;
  nb_poses_h: number;
  forme_speciale: boolean;
  actif: boolean;
  date_creation: string;
}

export type OutilDecoupeCreate = Omit<OutilDecoupeRead, "id" | "date_creation">;
export type OutilDecoupeUpdate = Partial<OutilDecoupeCreate>;

export const listOutilsDecoupe = (includeInactives = false) =>
  apiFetch<OutilDecoupeRead[]>(
    `/api/outils${includeInactives ? "?include_inactives=true" : ""}`
  );
export const getOutilDecoupe = (id: number) =>
  apiFetch<OutilDecoupeRead>(`/api/outils/${id}`);
export const createOutilDecoupe = (data: OutilDecoupeCreate) =>
  apiFetch<OutilDecoupeRead>("/api/outils", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateOutilDecoupe = (id: number, data: OutilDecoupeUpdate) =>
  apiFetch<OutilDecoupeRead>(`/api/outils/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const deleteOutilDecoupe = (id: number) =>
  apiFetch<void>(`/api/outils/${id}`, { method: "DELETE" });
export const reactiverOutilDecoupe = (id: number) =>
  apiFetch<OutilDecoupeRead>(`/api/outils/${id}/reactiver`, { method: "POST" });

// ---------------------------------------------------------------------------
// Sprint 9 v2 Lot 9c : Paramètres tarifaires (table tarif_poste)
// ---------------------------------------------------------------------------

export interface TarifPosteRead {
  id: number;
  cle: string;
  poste_numero: number;
  libelle: string;
  valeur_defaut: string; // Decimal renvoyé en string par FastAPI
  valeur_min: string | null;
  valeur_max: string | null;
  unite: string;
  actif: boolean;
  description: string | null;
  ordre_affichage: number;
  date_creation: string;
  date_maj: string;
}

export interface TarifPosteByPoste {
  poste_numero: number;
  libelle_poste: string;
  parametres: TarifPosteRead[];
}

export interface TarifsGrouped {
  postes: TarifPosteByPoste[];
}

export const getTarifsGrouped = () =>
  apiFetch<TarifsGrouped>("/api/tarif-poste");

export const updateTarifValeur = (cle: string, valeur_defaut: string) =>
  apiFetch<TarifPosteRead>(`/api/tarif-poste/${cle}`, {
    method: "PUT",
    body: JSON.stringify({ valeur_defaut }),
  });

export const resetPoste = (poste_numero: number) =>
  apiFetch<{ poste_numero: number; n_reset: number }>(
    `/api/tarif-poste/reset/${poste_numero}`,
    { method: "POST" }
  );

// ---------------------------------------------------------------------------
// Sprint 4 Lot 4b : Persistance Devis (CRUD /api/devis)
// ---------------------------------------------------------------------------

export type DevisStatut = "brouillon" | "valide";
export type DevisSort = "date_desc" | "date_asc" | "numero_asc" | "ht_desc";

// Snapshot du payload_input/payload_output côté API. Stocké en JSON donc
// on type minimal — la donnée est consommée par DevisResult / DevisCalculForm
// qui re-décodent comme DevisInput / DevisCalculResult.
type Json = Record<string, unknown>;

export interface DevisListItem {
  id: number;
  numero: string;
  date_creation: string;
  statut: DevisStatut;
  client_id: number | null;
  client_nom: string | null;
  machine_id: number;
  machine_nom: string;
  format_h_mm: string;
  format_l_mm: string;
  ht_total_eur: string;
  mode_calcul: string;
}

export interface DevisDetail {
  id: number;
  numero: string;
  date_creation: string;
  date_modification: string;
  statut: DevisStatut;
  client_id: number | null;
  client_nom: string | null;
  machine_id: number;
  machine_nom: string;
  payload_input: Json;
  payload_output: Json;
  mode_calcul: string;
  cylindre_choisi_z: number | null;
  cylindre_choisi_nb_etiq: number | null;
  format_h_mm: string;
  format_l_mm: string;
  ht_total_eur: string;
}

export interface DevisListResponse {
  items: DevisListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// Sprint 13 avenant — multi-lots production. Si `lots` fourni avec
// `quantite_totale`, le devis est créé avec N LotProduction (cascade).
// Validation côté backend : Σ qté lots == quantite_totale (422 sinon).
export interface LotProductionCreatePayload {
  cylindre_id: number;
  machine_id: number;
  nb_poses_dev: number;
  nb_poses_laize: number;
  sens_enroulement: number;
  quantite: number;
  matiere_id: number;
  intervalle_dev_reel_mm?: string | null;
  intervalle_laize_reel_mm?: string | null;
  largeur_plaque_mm?: string | null;
  score_optim?: number | null;
  cout_lot_ht_eur?: string | null;
}

export interface DevisCreate {
  payload_input: Json;
  payload_output: Json;
  client_id?: number | null;
  statut?: DevisStatut;
  cylindre_choisi_z?: number | null;
  cylindre_choisi_nb_etiq?: number | null;
  // Multi-lots (optionnel, backward-compat)
  quantite_totale?: number;
  lots?: LotProductionCreatePayload[];
}

export interface DevisUpdate {
  payload_input?: Json;
  payload_output?: Json;
  client_id?: number | null;
  statut?: DevisStatut;
  cylindre_choisi_z?: number | null;
  cylindre_choisi_nb_etiq?: number | null;
}

export interface ListDevisParams {
  page?: number;
  per_page?: number;
  search?: string;
  statut?: DevisStatut;
  sort?: DevisSort;
}

export const listDevis = (params: ListDevisParams = {}) => {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  if (params.search) qs.set("search", params.search);
  if (params.statut) qs.set("statut", params.statut);
  if (params.sort) qs.set("sort", params.sort);
  const suffix = qs.toString();
  return apiFetch<DevisListResponse>(
    `/api/devis${suffix ? `?${suffix}` : ""}`
  );
};

export const getDevisDetail = (id: number) =>
  apiFetch<DevisDetail>(`/api/devis/${id}`);

export const createDevis = (data: DevisCreate) =>
  apiFetch<DevisDetail>("/api/devis", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateDevis = (id: number, data: DevisUpdate) =>
  apiFetch<DevisDetail>(`/api/devis/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteDevis = (id: number) =>
  apiFetch<void>(`/api/devis/${id}`, { method: "DELETE" });

export const duplicateDevis = (id: number) =>
  apiFetch<DevisDetail>(`/api/devis/${id}/duplicate`, { method: "POST" });

// ---------------------------------------------------------------------------
// Sprint 12 Lot S12-D : Administration (admin only — get_current_admin)
// ---------------------------------------------------------------------------

export const listAdminUsers = () =>
  apiFetch<AdminUser[]>("/api/admin/users");

export const createAdminUser = (data: AdminUserCreate) =>
  apiFetch<AdminUser>("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const disableAdminUser = (id: number) =>
  apiFetch<AdminUser>(`/api/admin/users/${id}/disable`, { method: "PUT" });

export const enableAdminUser = (id: number) =>
  apiFetch<AdminUser>(`/api/admin/users/${id}/enable`, { method: "PUT" });

export const deleteAdminUser = (id: number) =>
  apiFetch<void>(`/api/admin/users/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Sprint 13 Lot S13.C : Onboarding express (catalogues pré-remplis)
// ---------------------------------------------------------------------------

export interface OnboardingMachineDefault {
  code: string;
  nom: string;
  marque?: string | null;
  modele?: string | null;
  repere_court?: string | null;
  laize_totale_mm: number;
  laize_utile_mm: number;
  nb_groupes_couleurs?: number | null;
  nb_postes_decoupe?: number | null;
  vitesse_nominale_constructeur_m_min?: number | null;
  vitesse_pratique_m_min: number;
  cout_horaire_eur?: number | null;
  options?: string[] | null;
  type_encre_supportee?: string[] | null;
  notes?: string | null;
}

export interface OnboardingMatiereDefault {
  code: string;
  libelle: string;
  categorie?: string | null;
  sous_type?: string | null;
  grammage_gm2?: number | null;
  epaisseur_microns?: number | null;
  adhesifs_compatibles?: string[] | null;
  est_transparent?: boolean | null;
  opacite_pct?: number | null;
  certifications_sanitaires?: string[] | null;
  certifications_env?: string[] | null;
  notes_techniques?: string | null;
}

export interface OnboardingOptionDefault {
  code: string;
  libelle: string;
  categorie?: string | null;
  description?: string | null;
  coef_vitesse_impact?: number | null;
  coef_gache_impact?: number | null;
  ajoute_temps_calage_min?: number | null;
  groupes_couleurs_requis?: number | null;
  modules_speciaux_requis?: string[] | null;
}

export interface OnboardingBaremeDefault {
  code: string;
  type: string;
  nom: string;
  notes?: string | null;
}

export interface OnboardingCatalogueDefaults {
  cylindres_developpes_mm: number[];
  machines: OnboardingMachineDefault[];
  matieres: OnboardingMatiereDefault[];
  options: OnboardingOptionDefault[];
  baremes: OnboardingBaremeDefault[];
}

export interface OnboardingInitRequest {
  cylindres_developpes_mm: number[];
  machines_codes: string[];
  matieres_codes: string[];
  options_codes: string[];
}

export interface OnboardingInitResponse {
  cylindres: number;
  machines: number;
  matieres: number;
  options: number;
  baremes: number;
  total: number;
}

export const getOnboardingCatalogueDefaults = () =>
  apiFetch<OnboardingCatalogueDefaults>(
    "/api/onboarding/catalogue-defaults"
  );

export const getOnboardingStatus = () =>
  apiFetch<{ catalogue_initialise: boolean }>("/api/onboarding/status");

export const postOnboardingInitialiser = (data: OnboardingInitRequest) =>
  apiFetch<OnboardingInitResponse>("/api/onboarding/initialiser-catalogues", {
    method: "POST",
    body: JSON.stringify(data),
  });

// ---------------------------------------------------------------------------
// Sprint 13 Lot S13.D : Moteur d'optimisation (POST /api/optimisation/calculer)
// ---------------------------------------------------------------------------

export interface OptimisationFormat {
  hauteur_mm: number;
  largeur_mm: number;
  rayon_angles_mm: number;
  forme_courbe: boolean;
}

export interface OptimisationContrainteClient {
  intervalle_dev_min_mm: number;
}

export type SensEnroulement =
  | "SE1"
  | "SE2"
  | "SE3"
  | "SE4"
  | "SE5"
  | "SE6"
  | "SE7"
  | "SE8";

export interface OptimisationCalculerRequest {
  format: OptimisationFormat;
  intervalle_dev_min_mm: number;
  nb_couleurs_impression: number;
  quantite: number;
  matiere_est_transparente?: boolean;
  options_codes: string[];
  contrainte_client: OptimisationContrainteClient;
  // PR #9.1 BAT
  mandrin_mm?: number;
  sens_enroulement?: SensEnroulement;
  epaisseur_matiere_um?: number;
  // PR Souveraineté commerciale (Règle 7)
  matiere_id?: number | null;
  epaisseur_matiere_force_um?: number | null;
  motif_forcage_epaisseur?: string | null;
  intervalle_laize_force_mm?: number | null;
  motif_forcage_intervalle_laize?: string | null;
  intervalle_dev_force_mm?: number | null;
  motif_forcage_intervalle_dev?: string | null;
  lacets_asymetriques?: boolean;
  lacet_droit_mm?: number | null;
  lacet_gauche_mm?: number | null;
  // Sprint 13 avenant : forçage nb poses laize (null = auto).
  nb_poses_laize_force?: number | null;
}

export interface OptimisationConfigOut {
  cylindre_id: number;
  machine_id: number;
  nb_poses_dev: number;
  nb_poses_laize: number;
  nb_poses_total: number;
  intervalle_dev_reel_mm: number;
  intervalle_laize_reel_mm: number;
  largeur_plaque_mm: number;
  z_mini_effet_banane: number;
  qualite_echenillage: string;
  consolidation_atteinte: boolean;
  intervalle_laize_souhaitable_mm: number | null;
  disposition_poses: string;
  coef_vitesse_echenillage: number;
  coef_gache_echenillage: number;
  coef_confort_rayon: number;
  coef_quinconce: number;
  coef_consolidation: number;
  coef_vitesse_options: number;
  coef_gache_options: number;
  coef_vitesse_final: number;
  coef_gache_final: number;
  score: number;
  // PR #9.1 BAT
  laize_plaque_mm: number;
  laize_papier_mm: number;
  chute_laterale_reelle_mm: number;
  z_cylindre_mm: number;
  nb_dents_cylindre: number;
  ml_total_m: number;
  m2_consomme: number;
  rendement_pct: number;
  diametre_bobine_mm: number;
  laize_liner_mm: number;
  sens_enroulement: SensEnroulement;
  // Libellé officiel flexo à afficher dans le BAT (ex: "0° Extérieur droite avant").
  sens_enroulement_libelle: string;
  // Rotations A en VUE A (planche presse) et VUE C (bobine fille client).
  // Mapping verrouillé 18/05/2026 — paires ext/int partagent même rotation.
  rotation_vue_a_deg: number;
  rotation_vue_c_deg: number;
  machines_compatibles: number[];
  noms_machines_compatibles: string[];
  // Brief #28 : badge informationnel UI étape 2. True si ≤ 80 dents.
  petit_cylindre: boolean;
  // Souveraineté commerciale
  intervalle_laize_recommande_mm: number;
  intervalle_laize_applique_mm: number;
  forcage_intervalle_laize: boolean;
  motif_forcage_intervalle_laize: string | null;
  intervalle_dev_recommande_mm: number;
  intervalle_dev_applique_mm: number;
  forcage_intervalle_dev: boolean;
  motif_forcage_intervalle_dev: string | null;
  lacet_droit_mm: number;
  lacet_gauche_mm: number;
  lacets_asymetriques: boolean;
  matiere: MatiereOut | null;
  epaisseur_appliquee_um: number;
  forcage_epaisseur: boolean;
  motif_forcage_epaisseur: string | null;
}

export interface OptimisationCalculerResponse {
  configurations: OptimisationConfigOut[];
  nb_candidats: number;
  message_filtrage: string | null;
  intervalle_dev_min_applique_mm: number;
  message_contrainte_client: string | null;
}

export const postOptimisationCalculer = (
  data: OptimisationCalculerRequest
) =>
  apiFetch<OptimisationCalculerResponse>("/api/optimisation/calculer", {
    method: "POST",
    body: JSON.stringify(data),
  });

export interface OptionDisponible {
  id: number;
  code: string;
  libelle: string;
  categorie: string | null;
  coef_vitesse_impact: number;
  coef_gache_impact: number;
}

export const getOptionsDisponibles = () =>
  apiFetch<OptionDisponible[]>("/api/optimisation/options-disponibles");

// ---------------------------------------------------------------------------
// Matières — catalogue tenant pour sélecteur /optimisation
// ---------------------------------------------------------------------------

export interface MatiereOut {
  id: number;
  code: string;
  libelle: string;
  categorie: string | null;
  sous_type: string | null;
  grammage_gm2: number | null;
  epaisseur_microns: number | null;
  est_transparent: boolean;
  opacite_pct: string | null;
  certifications_sanitaires: string[] | null;
  certifications_env: string[] | null;
  adhesifs_compatibles: string[] | null;
  actif: boolean;
}

export const listMatieres = () =>
  apiFetch<MatiereOut[]>("/api/matieres");

// ---------------------------------------------------------------------------
// Paramètres > Options de fabrication (CRUD tenant)
// ---------------------------------------------------------------------------

export interface OptionFabricationTenant {
  id: number;
  code: string;
  libelle: string;
  categorie: string | null;
  description: string | null;
  coef_vitesse_impact: string;
  coef_gache_impact: string;
  ajoute_temps_calage_min: number;
  forfait_eur: string | null;
  prix_au_m2_eur: string | null;
  prix_au_mille_eur: string | null;
  cout_consommable_eur: string | null;
  actif: boolean;
  valeur_recommandee_origine: {
    coef_vitesse_impact: number;
    coef_gache_impact: number;
    ajoute_temps_calage_min: number;
  } | null;
}

export interface OptionFabricationUpdatePayload {
  coef_vitesse_impact?: string;
  coef_gache_impact?: string;
  forfait_eur?: string | null;
  prix_au_m2_eur?: string | null;
  prix_au_mille_eur?: string | null;
  cout_consommable_eur?: string | null;
  actif?: boolean;
}

export const listOptionsFabrication = () =>
  apiFetch<OptionFabricationTenant[]>("/api/parametres/options-fabrication");

export const createOptionFromMaster = (code: string) =>
  apiFetch<OptionFabricationTenant>(
    `/api/parametres/options-fabrication/from-master/${encodeURIComponent(code)}`,
    { method: "POST" }
  );

export const updateOptionFabrication = (
  id: number,
  payload: OptionFabricationUpdatePayload
) =>
  apiFetch<OptionFabricationTenant>(
    `/api/parametres/options-fabrication/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );

export const deleteOptionFabrication = (id: number) =>
  apiFetch<OptionFabricationTenant>(
    `/api/parametres/options-fabrication/${id}`,
    { method: "DELETE" }
  );

// ---------------------------------------------------------------------------
// Sprint 13 Lot S13.E : POC IA analyse photo etiquette (FlexoCheck)
// ---------------------------------------------------------------------------

export interface IACouleurDetectee {
  rgb_approximatif: string;
  pantone_proche_estime: string | null;
  surface_pct: number;
  /**
   * Fix analyseur photo : true si la teinte correspond à la réserve papier
   * (défonce sur support opaque clair) plutôt qu'à une encre blanche
   * imprimée. Calculé côté backend par appliquer_support_reserve().
   * L'UI affiche un badge "Réserve papier" et permet à l'utilisateur
   * d'override (toggle "Considérer comme encre blanche") avec recalcul
   * dynamique des min/max stations sans rappel API.
   */
  support_reserve?: boolean;
}

export interface IAMatiereEstimee {
  type: string;
  couleur: string;
  finition_apparente: string;
}

export interface IAResultatsAnalyse {
  couleurs_detectees: IACouleurDetectee[];
  nombre_couleurs_distinctes: number;
  couleurs_min_technique: number;
  couleurs_max_technique: number;
  techniques_impression_estimees: string[];
  matiere_estimee: IAMatiereEstimee;
  finitions_visibles: string[];
  presence_blanc_opaque: boolean;
  niveau_confiance: "haut" | "moyen" | "faible";
  limites_analyse: string[];
}

export interface IAAnalysePhotoRequest {
  image_base64: string;
  mime_type: string;
  devis_id?: number | null;
  /** Nom du fichier d'origine (feat historique analyses). */
  image_filename?: string | null;
}

export interface IAAnalysePhotoResponse {
  id: number;
  resultats_ia: IAResultatsAnalyse;
  niveau_confiance: string;
  nombre_couleurs_distinctes: number | null;
  model_utilise: string | null;
  created_at: string;
}

export const postIAAnalyserPhoto = (data: IAAnalysePhotoRequest) =>
  apiFetch<IAAnalysePhotoResponse>("/api/ia/analyser-photo", {
    method: "POST",
    body: JSON.stringify(data),
  });

// ---------------------------------------------------------------------------
// Feat historique analyses — list / get / delete / serve photo
// ---------------------------------------------------------------------------

export interface IAAnalyseListItem {
  id: number;
  image_filename: string | null;
  image_key: string | null;
  photo_mime_type: string | null;
  image_size_bytes: number | null;
  niveau_confiance: string | null;
  nombre_couleurs_distinctes: number | null;
  erreur: string | null;
  created_at: string;
}

export interface IAAnalyseListResponse {
  items: IAAnalyseListItem[];
  page: number;
  limit: number;
  total: number;
}

export interface IAAnalyseDetail {
  id: number;
  image_filename: string | null;
  image_key: string | null;
  photo_mime_type: string | null;
  image_size_bytes: number | null;
  resultats_ia: IAResultatsAnalyse;
  niveau_confiance: string | null;
  nombre_couleurs_distinctes: number | null;
  model_utilise: string | null;
  erreur: string | null;
  devis_id: number | null;
  created_at: string;
}

export const listIAAnalyses = (page = 1, limit = 20) =>
  apiFetch<IAAnalyseListResponse>(
    `/api/ia/analyses?page=${page}&limit=${limit}`
  );

export const getIAAnalyse = (id: number) =>
  apiFetch<IAAnalyseDetail>(`/api/ia/analyses/${id}`);

export const deleteIAAnalyse = (id: number) =>
  apiFetch<void>(`/api/ia/analyses/${id}`, { method: "DELETE" });

/**
 * Récupère le blob de la photo authentifiée et retourne un object URL
 * utilisable en src d'<img>. `<img src="/api/ia/photos/...">` standard
 * ne passe pas le Bearer JWT — d'où ce helper qui fait un fetch + revoke
 * géré par le composant appelant via URL.revokeObjectURL.
 */
export async function fetchIAPhotoBlob(image_key: string): Promise<string> {
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem("devis_flexo_access_token")
      : null;
  const r = await fetch(
    `${API_URL}/api/ia/photos/${encodeURIComponent(image_key)}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );
  if (!r.ok) {
    throw new ApiError(
      r.status,
      `GET /api/ia/photos/${image_key} → ${r.status} ${r.statusText}`
    );
  }
  const blob = await r.blob();
  return URL.createObjectURL(blob);
}

// ---------------------------------------------------------------------------
// Brief #29 — Paramètres parc : cylindres
// ---------------------------------------------------------------------------

export interface CylindreParc {
  id: number;
  nb_dents: number;
  developpe_mm: string;
  actif: boolean;
  notes: string | null;
  date_creation: string;
}

export interface CylindreCreatePayload {
  nb_dents: number;
  actif?: boolean;
  notes?: string | null;
}

export type CylindreUpdatePayload = Partial<CylindreCreatePayload>;

export const listCylindres = (actif: boolean | null = true) => {
  const params = new URLSearchParams();
  if (actif === false) params.set("actif", "false");
  else if (actif === null) params.set("actif", "");
  return apiFetch<CylindreParc[]>(
    `/api/cylindres${params.toString() ? `?${params}` : ""}`
  );
};
export const createCylindre = (data: CylindreCreatePayload) =>
  apiFetch<CylindreParc>("/api/cylindres", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updateCylindre = (id: number, data: CylindreUpdatePayload) =>
  apiFetch<CylindreParc>(`/api/cylindres/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
export const deleteCylindre = (id: number) =>
  apiFetch<void>(`/api/cylindres/${id}`, { method: "DELETE" });
export const toggleActifCylindre = (id: number) =>
  apiFetch<CylindreParc>(`/api/cylindres/${id}/toggle-actif`, {
    method: "POST",
  });

// ---------------------------------------------------------------------------
// Brief #30 — Paramètres parc : porte-clichés (cyls engrenage synchronisés)
// ---------------------------------------------------------------------------
// Refonte vs Brief #29 : schéma porté sur machine_id + cylindre_id + quantite
// (et non plus sur marque/modele/laize_utile_mm/matiere — interprétation
// métier corrigée, cf docs/Brief_CC_30_PorteCliche_UI_BoutonDevis.md).

export interface PorteCliche {
  id: number;
  machine_id: number;
  machine_nom: string;
  machine_nb_couleurs: number | null;
  cylindre_id: number;
  cylindre_nb_dents: number;
  cylindre_developpe_mm: string;
  quantite: number;
  notes: string | null;
  actif: boolean;
  created_at: string;
  updated_at: string;
}

export interface PorteClicheCreatePayload {
  machine_id: number;
  cylindre_id: number;
  // Si non fourni, le backend pose default = machine.nb_groupes_couleurs.
  quantite?: number;
  notes?: string | null;
  actif?: boolean;
}

export interface PorteClicheUpdatePayload {
  quantite?: number;
  notes?: string | null;
  actif?: boolean;
}

export const listPorteCliches = (
  options: { actif?: boolean | null; machine_id?: number } = {}
) => {
  const { actif = true, machine_id } = options;
  const params = new URLSearchParams();
  if (actif === false) params.set("actif", "false");
  else if (actif === null) params.set("actif", "");
  if (machine_id !== undefined) params.set("machine_id", String(machine_id));
  return apiFetch<PorteCliche[]>(
    `/api/porte-cliches${params.toString() ? `?${params}` : ""}`
  );
};
export const createPorteCliche = (data: PorteClicheCreatePayload) =>
  apiFetch<PorteCliche>("/api/porte-cliches", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const updatePorteCliche = (
  id: number,
  data: PorteClicheUpdatePayload
) =>
  apiFetch<PorteCliche>(`/api/porte-cliches/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
export const deletePorteCliche = (id: number) =>
  apiFetch<void>(`/api/porte-cliches/${id}`, { method: "DELETE" });
export const toggleActifPorteCliche = (id: number) =>
  apiFetch<PorteCliche>(`/api/porte-cliches/${id}/toggle-actif`, {
    method: "POST",
  });
