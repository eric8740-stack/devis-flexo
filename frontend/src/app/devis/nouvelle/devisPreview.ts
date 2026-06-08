// Lot front A — devis page unique réactive.
//
// Couche d'adaptation entre l'état (partiel) de la page et l'endpoint LIVE
// `POST /api/devis/preview` (#124, read-only, cost_engine SSOT) :
//   - `buildPreviewRequest` : état page → body wire (nb_couleurs objet, champs
//     absents = null car le schéma backend impose `gt=0` + `extra="forbid"`).
//   - `parsePreview` : réponse wire → nombres (les Decimal arrivent en CHAÎNES,
//     nullables quand l'état est trop partiel pour chiffrer).
//   - `previewDevisLive` : enchaîne les deux, honore l'AbortSignal.
//   - `posesPourPersist` : poses best-effort pour le POST /devis (le backend
//     reste autoritaire ; même formule géométrique que `preview_devis`).

import {
  previewDevis,
  type CylindreParc,
  type DevisPreviewOut,
  type DevisPreviewRequest,
  type NbCouleursIn,
} from "@/lib/api";

const INTERVALLE_DEV_MM = 2;
const INTERVALLE_LAIZE_MM = 3;
const LAIZE_PRESSE_DEFAUT_MM = 330;

// ── État page (saisie) ───────────────────────────────────────────────

export interface DevisPreviewInput {
  laize_mm: number;
  dev_mm: number;
  forme: string | null;
  quantite: number;
  nb_couleurs: number;
  cylindre_id: number | null;
  machine_id: number | null;
  matiere_id: number | null;
  epaisseur_um: number | null;
  mandrin_mm: number;
  diam_max_mm: number | null;
  nb_filles_force: number | null;
  mode_sans_outil: boolean;
  laize_stock_mm: number | null;
  finitions: string[];
}

// ── Résultat parsé (consommé par l'UI) ───────────────────────────────

export interface DevisPreviewGeometrie {
  diametre_mm: number | null;
  nb_poses: number | null;
  nb_filles: number | null;
  dechet_lateral_mm: number | null;
}

export interface DevisPreviewDecompoLigne {
  poste: string;
  montant: number;
}

export interface DevisPreviewOptionCout {
  code: string;
  delta_eur: number;
}

export interface DevisPreviewAlerte {
  niveau: "info" | "warn";
  message: string;
}

export interface DevisPreviewResult {
  prix_ht: number | null;
  cout_revient: number | null;
  marge_pct: number | null; // pourcentage (ex. 30), pas une fraction
  prix_1000: number | null;
  geometrie: DevisPreviewGeometrie;
  decompo: DevisPreviewDecompoLigne[];
  options: DevisPreviewOptionCout[];
  alertes: DevisPreviewAlerte[];
}

// ── Helpers ──────────────────────────────────────────────────────────

const numOrNull = (s: string | null): number | null =>
  s === null || s.trim() === "" ? null : Number(s);

/** Un cylindre est « compatible » avec le format si son développé permet au
 * moins une pose en dev (développé ≥ dev + intervalle). Filtre purement
 * géométrique côté front pour alimenter le select Outil. */
export function cylindresCompatibles(
  cylindres: CylindreParc[],
  devMm: number,
  intervalleDevMm: number = INTERVALLE_DEV_MM,
): CylindreParc[] {
  const pas = devMm + intervalleDevMm;
  if (pas <= 0) return cylindres;
  return cylindres.filter((c) => parseFloat(c.developpe_mm) >= pas);
}

function nbCouleursObj(n: number): NbCouleursIn {
  // UI A1 : un seul compteur « impression » (process quadri). Pantone /
  // blanc / vernis = 0 (affinables en A2 si besoin).
  return { impression: n, pantone: 0, blanc: 0, vernis: 0 };
}

/** État page → body wire. Champs absents/invalides → `null` (le backend les
 * traite best-effort ; il refuse 0 via `gt=0`). `finitions: []` en A1 (la
 * saisie de leurs montants ST arrive en A2 ; la persistance passe par
 * `options_codes_etape4`). */
export function buildPreviewRequest(i: DevisPreviewInput): DevisPreviewRequest {
  return {
    laize: i.laize_mm > 0 ? i.laize_mm : null,
    dev: i.dev_mm > 0 ? i.dev_mm : null,
    forme: i.forme ?? null,
    quantite: i.quantite > 0 ? i.quantite : null,
    cylindre_id: i.mode_sans_outil ? null : i.cylindre_id,
    machine_id: i.machine_id ?? null,
    matiere_id: i.matiere_id ?? null,
    epaisseur_um:
      i.epaisseur_um && i.epaisseur_um > 0 ? Math.round(i.epaisseur_um) : null,
    mandrin_mm: i.mandrin_mm > 0 ? Math.round(i.mandrin_mm) : null,
    diam_max_mm:
      i.diam_max_mm && i.diam_max_mm > 0 ? Math.round(i.diam_max_mm) : null,
    nb_filles_force: i.nb_filles_force ?? null,
    mode_sans_outil: i.mode_sans_outil,
    laize_stock_mm:
      i.laize_stock_mm && i.laize_stock_mm > 0 ? i.laize_stock_mm : null,
    nb_couleurs: i.nb_couleurs > 0 ? nbCouleursObj(i.nb_couleurs) : null,
    finitions: [],
  };
}

/** Réponse wire (Decimal en chaînes, nullables) → nombres pour l'UI. */
export function parsePreview(out: DevisPreviewOut): DevisPreviewResult {
  return {
    prix_ht: numOrNull(out.prix_ht),
    cout_revient: numOrNull(out.cout_revient),
    marge_pct: numOrNull(out.marge_pct),
    prix_1000: numOrNull(out.prix_1000),
    geometrie: {
      diametre_mm: out.geometrie.diametre_mm,
      nb_poses: out.geometrie.nb_poses,
      nb_filles: out.geometrie.nb_filles,
      dechet_lateral_mm: out.geometrie.dechet_lateral_mm,
    },
    decompo: out.decompo.map((l) => ({
      poste: l.poste,
      montant: Number(l.montant),
    })),
    options: out.options.map((o) => ({
      code: o.code,
      delta_eur: Number(o.delta_eur),
    })),
    alertes: out.alertes.map((a) => ({ niveau: a.niveau, message: a.message })),
  };
}

/** Preview LIVE — POST /api/devis/preview (read-only), honore l'AbortSignal. */
export async function previewDevisLive(
  input: DevisPreviewInput,
  opts: { signal?: AbortSignal } = {},
): Promise<DevisPreviewResult> {
  const out = await previewDevis(buildPreviewRequest(input), opts.signal);
  return parsePreview(out);
}

/** Poses best-effort pour le POST /devis (le backend reste autoritaire) —
 * même géométrie que `preview_devis` : floor(dev) en développé, floor(laize)
 * en largeur, `nb_filles_force` prioritaire en sans outil. */
export function posesPourPersist(
  input: DevisPreviewInput,
  cylindreDeveloppeMm: number | null,
): { nb_poses_dev: number; nb_poses_laize: number } {
  const laizeUtile = input.laize_stock_mm ?? LAIZE_PRESSE_DEFAUT_MM;
  let posesDev = 1;
  let posesLaize = 1;
  if (cylindreDeveloppeMm && input.dev_mm > 0) {
    posesDev = Math.max(
      1,
      Math.floor(cylindreDeveloppeMm / (input.dev_mm + INTERVALLE_DEV_MM)),
    );
  }
  if (input.laize_mm > 0) {
    posesLaize = Math.max(
      1,
      Math.floor(laizeUtile / (input.laize_mm + INTERVALLE_LAIZE_MM)),
    );
  }
  if (input.mode_sans_outil && input.nb_filles_force) {
    posesLaize = input.nb_filles_force;
  }
  return { nb_poses_dev: posesDev, nb_poses_laize: posesLaize };
}
