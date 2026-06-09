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
  // Codes des options de fabrication sélectionnées (chips finitions).
  options_codes: string[];
  // Lot C : la config choisie pilote la preview via cylindre_id/machine_id
  // (résolus depuis le parc), PAS via un champ dédié — `/preview` est
  // `extra="forbid"`. config_id / écarts forcés ne sont pas envoyés.
  // V0 — leviers commerciaux : marge override (%, null = défaut tenant) +
  // remise commerciale (%).
  marge_pct_override: number | null;
  remise_pct: number;
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
  // null = option à impact production sans forfait → « chiffré bientôt ».
  delta_eur: number | null;
  impact_production: boolean;
}

export interface DevisPreviewAlerte {
  niveau: "info" | "warn";
  message: string;
}

// Lot C — config cylindre×machine candidate (pose + score), parsée.
export interface DevisPreviewConfig {
  id: string; // identifiant composite du back (ex. "1-1-4x2")
  cylindre_dents: number;
  developpe_mm: number;
  machine: string;
  poses_laize: number;
  poses_dev: number;
  poses_total: number;
  delta_dev_mm: number;
  delta_laize_mm: number;
  sens: number;
  score: number;
  recommande: boolean;
}

// Lot C — écarts entre étiquettes (défauts moteur, surchargeables Règle 7).
export interface DevisPreviewEcarts {
  intervalle_laize_mm: number;
  intervalle_dev_mm: number;
  nb_poses_laize: "auto" | number;
  force_intervalle_laize: boolean;
}

// V0 — décompo coût regroupée (5 lignes), parsée.
export interface DevisPreviewDecompoGroupee {
  matiere_p1: number;
  impression_presse_calage: number;
  cliches_outil: number;
  option_finitions: number;
  refente: number;
}

export interface DevisPreviewResult {
  prix_ht: number | null; // HT brut (7 postes)
  cout_revient: number | null;
  marge_pct: number | null; // pourcentage (ex. 30), pas une fraction
  prix_1000: number | null;
  geometrie: DevisPreviewGeometrie;
  decompo: DevisPreviewDecompoLigne[];
  options: DevisPreviewOptionCout[];
  alertes: DevisPreviewAlerte[];
  // Lot C — vides sur l'ancien endpoint (dégradation propre).
  configs: DevisPreviewConfig[];
  ecarts: DevisPreviewEcarts | null;
  // V0 — remise tracée à part + HT net + décompo groupée.
  remise_pct: number;
  remise_eur: number | null;
  prix_ht_net: number | null;
  decompo_groupee: DevisPreviewDecompoGroupee | null;
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
 * traite best-effort ; il refuse 0 via `gt=0`). Les options partent en
 * `options_codes` (le serveur price) ; `finitions` reste vide (réservé aux
 * forfaits ST ad-hoc). */
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
    // Options par CODE (#130) : le serveur price. Forfaits ad-hoc inutilisés.
    options_codes: i.options_codes,
    finitions: [],
    // V0 — marge override seulement si saisie ; remise toujours (défaut 0).
    marge_pct:
      i.marge_pct_override !== null && i.marge_pct_override >= 0
        ? i.marge_pct_override
        : null,
    remise_pct: i.remise_pct > 0 ? i.remise_pct : 0,
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
      delta_eur: numOrNull(o.delta_eur),
      impact_production: o.impact_production,
    })),
    alertes: out.alertes.map((a) => ({ niveau: a.niveau, message: a.message })),
    // Lot C — parse défensif (les numériques peuvent arriver en string ou
    // number selon le back) ; absents sur l'ancien endpoint → [] / null.
    configs: (out.configs ?? []).map((c) => ({
      id: String(c.id),
      cylindre_dents: Number(c.cylindre_dents),
      developpe_mm: Number(c.developpe_mm),
      machine: c.machine,
      poses_laize: Number(c.poses_laize),
      poses_dev: Number(c.poses_dev),
      poses_total: Number(c.poses_total),
      delta_dev_mm: Number(c.delta_dev_mm),
      delta_laize_mm: Number(c.delta_laize_mm),
      sens: Number(c.sens),
      score: Number(c.score),
      recommande: Boolean(c.recommande),
    })),
    ecarts: out.ecarts
      ? {
          intervalle_laize_mm: Number(out.ecarts.intervalle_laize_mm),
          intervalle_dev_mm: Number(out.ecarts.intervalle_dev_mm),
          nb_poses_laize:
            out.ecarts.nb_poses_laize === "auto"
              ? "auto"
              : Number(out.ecarts.nb_poses_laize),
          force_intervalle_laize: Boolean(out.ecarts.force_intervalle_laize),
        }
      : null,
    // V0 — remise / HT net / décompo groupée (absents sur ancien endpoint).
    remise_pct: out.remise_pct != null ? Number(out.remise_pct) : 0,
    remise_eur: numOrNull(out.remise_eur ?? null),
    prix_ht_net: numOrNull(out.prix_ht_net ?? null),
    decompo_groupee: out.decompo_groupee
      ? {
          matiere_p1: Number(out.decompo_groupee.matiere_p1),
          impression_presse_calage: Number(
            out.decompo_groupee.impression_presse_calage,
          ),
          cliches_outil: Number(out.decompo_groupee.cliches_outil),
          option_finitions: Number(out.decompo_groupee.option_finitions),
          refente: Number(out.decompo_groupee.refente),
        }
      : null,
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
