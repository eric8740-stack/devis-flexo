// URL du backend FastAPI.
// - En dev local : http://localhost:8000 (défaut)
// - En prod (Vercel) : NEXT_PUBLIC_API_URL définie dans les env vars Vercel,
//   pointant sur l'URL Railway du backend (ex: https://devis-flexo.up.railway.app)
const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export const STATUTS_MACHINE = ["actif", "inactif", "maintenance"] as const;
export type StatutMachine = (typeof STATUTS_MACHINE)[number];

export interface Machine {
  id: number;
  nom: string;
  largeur_max_mm: number | null;
  vitesse_max_m_min: number | null;
  nb_couleurs: number | null;
  cout_horaire_eur: number | null;
  statut: StatutMachine;
  commentaire: string | null;
  date_creation: string;
  date_maj: string;
}

export type MachineCreate = Omit<Machine, "id" | "date_creation" | "date_maj">;
export type MachineUpdate = Partial<MachineCreate>;

export const listMachines = () => apiFetch<Machine[]>("/api/machines?limit=200");
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
export const STATUTS_PARTENAIRE = ["actif", "inactif"] as const;
export type StatutPartenaire = (typeof STATUTS_PARTENAIRE)[number];

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
  statut: StatutPartenaire;
  date_creation: string;
  date_maj: string;
}

export type PartenaireSTCreate = Omit<
  PartenaireST,
  "id" | "date_creation" | "date_maj"
>;
export type PartenaireSTUpdate = Partial<PartenaireSTCreate>;

export const listPartenairesST = () =>
  apiFetch<PartenaireST[]>("/api/partenaires-st?limit=200");
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
export const STATUTS_COMPLEXE = ["actif", "archive"] as const;
export type StatutComplexe = (typeof STATUTS_COMPLEXE)[number];

export interface Complexe {
  id: number;
  reference: string;
  famille: FamilleComplexe;
  face_matiere: string | null;
  grammage_g_m2: number | null;
  adhesif_type: string | null;
  prix_m2_eur: number;
  fournisseur_id: number | null;
  statut: StatutComplexe;
  commentaire: string | null;
  date_creation: string;
  date_maj: string;
}

export type ComplexeCreate = Omit<Complexe, "id" | "date_creation" | "date_maj">;
export type ComplexeUpdate = Partial<ComplexeCreate>;

export const listComplexes = () =>
  apiFetch<Complexe[]>("/api/complexes?limit=200");
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
  postes: PosteResult[];
  cout_revient_eur: string;
  pct_marge_appliquee: string;
  prix_vente_ht_eur: string;
  // Sprint 5 Lot 5c — livrable commercial clé (Note 9 mémoire).
  prix_au_mille_eur: string;
}

export const calculerDevis = (input: DevisInput) =>
  apiFetch<DevisOutput>("/api/cost/calculer", {
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

export const listOutilsDecoupe = () =>
  apiFetch<OutilDecoupeRead[]>("/api/outils");
