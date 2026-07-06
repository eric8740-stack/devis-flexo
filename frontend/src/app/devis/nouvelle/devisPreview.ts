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
  // Lot C-inputs (#140) — config choisie (id composite) + forçage écarts. Le
  // serveur fige la pose / surcharge les écarts → la marge bouge en direct.
  config_id: string | null;
  intervalle_laize_mm: number | null;
  force_intervalle_laize: boolean;
  nb_poses_laize_force: number | null;
  // V0 — leviers commerciaux : marge override (%, null = défaut tenant) +
  // remise commerciale (%).
  marge_pct_override: number | null;
  remise_pct: number;
  // Lot F (#147) — ml par bobine (livraison) + Ø mandrin bobinage.
  ml_par_bobine: number | null;
  diametre_mandrin_mm: number | null;
  // Lot F2 — nb de bobines imposé (mode de livraison). EXCLUSIF avec
  // `ml_par_bobine` : si imposé (≥ 1), `ml_par_bobine` est OMIS du payload
  // (jamais les deux — le back dérive le ml/bobine).
  nb_bobines_impose: number | null;
}

// ── Résultat parsé (consommé par l'UI) ───────────────────────────────

export interface DevisPreviewGeometrie {
  diametre_mm: number | null;
  nb_poses: number | null;
  nb_filles: number | null;
  dechet_lateral_mm: number | null;
  // Lot E — épaisseur utilisée pour le Ø + flag fallback (absents = false/null).
  epaisseur_utilisee_microns: number | null;
  epaisseur_fallback: boolean;
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

// Lot F — bobinage/appro parsé (tout en nombres).
export interface DevisPreviewBobinage {
  ml_total: number;
  m2_total: number;
  ml_par_bobine: number;
  nb_bobines: number;
  diametre_bobine_mm: number;
  diametre_mandrin_mm: number;
  diametre_max_presse_mm: number;
  depasse_max: boolean;
  nb_changements: number;
  temps_arret_min: number;
  // Lot F2 — présents UNIQUEMENT en mode imposé (clés absentes de la réponse
  // sinon, y compris back plus ancien) → null = pas de bandeau surplus.
  nb_bobines_production: number | null;
  surplus_bobines: number | null;
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
  // Lot F — bobinage/appro (null si back F absent).
  bobinage: DevisPreviewBobinage | null;
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
  // Lot F2 — imposé valide (entier ≥ 1) ou null.
  const nbBobinesImpose =
    i.nb_bobines_impose !== null && i.nb_bobines_impose >= 1
      ? Math.round(i.nb_bobines_impose)
      : null;
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
    // Lot C-inputs (#140) — config épingle la pose ; forçage écarts dans les
    // bornes du schéma (sinon non envoyé → évite 422). Pas de config en sans
    // outil (pas d'outil de découpe).
    config_id: i.mode_sans_outil ? null : (i.config_id ?? null),
    force_intervalle_laize: i.force_intervalle_laize,
    intervalle_laize_mm:
      i.force_intervalle_laize &&
      i.intervalle_laize_mm !== null &&
      i.intervalle_laize_mm > 0 &&
      i.intervalle_laize_mm <= 50
        ? i.intervalle_laize_mm
        : null,
    nb_poses_laize_force:
      i.nb_poses_laize_force !== null &&
      i.nb_poses_laize_force >= 1 &&
      i.nb_poses_laize_force <= 20
        ? i.nb_poses_laize_force
        : null,
    // V0 — marge override seulement si saisie ; remise toujours (défaut 0).
    marge_pct:
      i.marge_pct_override !== null && i.marge_pct_override >= 0
        ? i.marge_pct_override
        : null,
    remise_pct: i.remise_pct > 0 ? i.remise_pct : 0,
    // Lot F (#147) / F2 — EXCLUSIFS : jamais les deux dans le payload. Imposé
    // actif → `nb_bobines_impose` seul (`ml_par_bobine` OMIS, pas null) ;
    // sinon `ml_par_bobine` (int gt 0, sinon null → défaut entreprise).
    ...(nbBobinesImpose !== null
      ? { nb_bobines_impose: nbBobinesImpose }
      : {
          ml_par_bobine:
            i.ml_par_bobine !== null && i.ml_par_bobine > 0
              ? Math.round(i.ml_par_bobine)
              : null,
        }),
    diametre_mandrin_mm:
      i.diametre_mandrin_mm !== null && i.diametre_mandrin_mm > 0
        ? Math.round(i.diametre_mandrin_mm)
        : null,
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
      epaisseur_utilisee_microns:
        out.geometrie.epaisseur_utilisee_microns ?? null,
      epaisseur_fallback: out.geometrie.epaisseur_fallback ?? false,
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
    // Lot F — bobinage/appro (parse défensif ; null si back F absent).
    bobinage: out.bobinage
      ? {
          ml_total: Number(out.bobinage.ml_total),
          m2_total: Number(out.bobinage.m2_total),
          ml_par_bobine: Number(out.bobinage.ml_par_bobine),
          nb_bobines: Number(out.bobinage.nb_bobines),
          diametre_bobine_mm: Number(out.bobinage.diametre_bobine_mm),
          diametre_mandrin_mm: Number(out.bobinage.diametre_mandrin_mm),
          diametre_max_presse_mm: Number(out.bobinage.diametre_max_presse_mm),
          depasse_max: Boolean(out.bobinage.depasse_max),
          nb_changements: Number(out.bobinage.nb_changements),
          temps_arret_min: Number(out.bobinage.temps_arret_min),
          // Lot F2 — clés ABSENTES sans imposé (dont back plus ancien) → null.
          nb_bobines_production:
            out.bobinage.nb_bobines_production != null
              ? Number(out.bobinage.nb_bobines_production)
              : null,
          surplus_bobines:
            out.bobinage.surplus_bobines != null
              ? Number(out.bobinage.surplus_bobines)
              : null,
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
