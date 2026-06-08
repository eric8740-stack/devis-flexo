// Lot front A — devis page unique réactive.
//
// ⚠️ MOCK du contrat « live preview » tant que l'endpoint backend CC1
// `POST /api/devis/preview` (#124) n'est pas mergé + déployé. Tout est ISOLÉ
// ici : la shape de `DevisPreviewInput` / `DevisPreviewResult` est le CONTRAT
// FINAL tranché avec CC1. Au swap, on remplace le corps de `previewDevisLive`
// par un `apiFetch<DevisPreviewResult>("/api/devis/preview", …, { signal })`
// SANS toucher l'UI (zéro friction).
//
// Le calcul est une APPROXIMATION déterministe (pas le cost_engine sacré) :
// il rend la page réactive (hero prix + €/1000 + marge + décompo + géométrie
// + coût marginal par option + alertes). Les vrais chiffres viennent du back.

import type { CylindreParc } from "@/lib/api";

// ── Contrat /api/devis/preview ───────────────────────────────────────

/** Niveau d'alerte douce (info bleu / attention ambre / bloquant rouge). */
export type DevisPreviewNiveau = "info" | "attention" | "bloquant";

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

export interface DevisPreviewGeometrie {
  diametre_mm: number;
  nb_poses: number;
  nb_filles: number;
  dechet_lateral_mm: number;
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
  niveau: DevisPreviewNiveau;
  message: string;
}

export interface DevisPreviewResult {
  prix_ht: number;
  cout_revient: number;
  marge_pct: number;
  prix_1000: number;
  geometrie: DevisPreviewGeometrie;
  decompo: DevisPreviewDecompoLigne[];
  // Coût marginal de chaque finition active (« + X € »), en UN appel.
  options: DevisPreviewOptionCout[];
  // Coût marginal d'une couleur d'impression supplémentaire.
  couleur_plus: number;
  alertes: DevisPreviewAlerte[];
}

/** Contexte mock-only : le vrai endpoint résout le développé depuis
 * `cylindre_id` côté serveur. En mock on lui passe le développé résolu pour
 * la géométrie. Le swap réseau ignore ce paramètre. */
export interface DevisPreviewMockCtx {
  cylindre_developpe_mm?: number | null;
}

const MARGE_DEFAUT_PCT = 0.3; // mock (le vrai vient de ConfigCouts)
const PRIX_M2_DEFAUT_EUR = 0.35; // mock (le vrai vient du complexe matière)
const INTERVALLE_DEV_MM = 2;
const INTERVALLE_LAIZE_MM = 3;
const LAIZE_PRESSE_DEFAUT_MM = 330;

const round2 = (n: number) => Math.round(n * 100) / 100;
const round1 = (n: number) => Math.round(n * 10) / 10;

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

function nbPosesDev(developpeMm: number, pasDevMm: number): number {
  if (pasDevMm <= 0 || developpeMm < pasDevMm) return 0;
  return Math.floor(developpeMm / pasDevMm);
}

/** Coût marginal mock d'une finition — déterministe, varié par code (pas de
 * hasard, stable d'un appel à l'autre). */
function optionDelta(code: string, quantite: number): number {
  let h = 0;
  for (let i = 0; i < code.length; i++) {
    h = (h + code.charCodeAt(i) * (i + 1)) % 97;
  }
  const base = 15 + (h % 26); // 15–40 € fixe
  const variable = (quantite / 1000) * 0.8; // par mille
  return round2((base + variable) / (1 - MARGE_DEFAUT_PCT));
}

/** Approximation déterministe du devis pour la preview live (MOCK). Renvoie
 * TOUJOURS la shape complète du contrat ; les états partiels sont signalés
 * via `alertes` (le front « skip » l'appel sous le minimum laize/dev/qté). */
export function computeDevisPreview(
  input: DevisPreviewInput,
  ctx: DevisPreviewMockCtx = {},
): DevisPreviewResult {
  const {
    laize_mm,
    dev_mm,
    quantite,
    nb_couleurs,
    mode_sans_outil,
    laize_stock_mm,
    nb_filles_force,
    matiere_id,
    cylindre_id,
    mandrin_mm,
    finitions,
  } = input;
  const cylindreDeveloppe = ctx.cylindre_developpe_mm ?? null;

  const alertes: DevisPreviewAlerte[] = [];

  // Sous le minimum géométrique → pas de prix (jamais de faux « 0,00 € »).
  if (!(laize_mm > 0) || !(dev_mm > 0) || !(quantite > 0)) {
    return {
      prix_ht: 0,
      cout_revient: 0,
      marge_pct: MARGE_DEFAUT_PCT,
      prix_1000: 0,
      geometrie: {
        diametre_mm: 0,
        nb_poses: 0,
        nb_filles: 0,
        dechet_lateral_mm: 0,
      },
      decompo: [],
      options: [],
      couleur_plus: 0,
      alertes: [
        {
          niveau: "bloquant",
          message: "Renseigne laize, développé et quantité pour estimer le prix.",
        },
      ],
    };
  }

  // ── Géométrie ───────────────────────────────────────────────────
  const laizePresse = laize_stock_mm ?? LAIZE_PRESSE_DEFAUT_MM;
  const posesLaizeGeom = Math.max(
    1,
    Math.floor(laizePresse / (laize_mm + INTERVALLE_LAIZE_MM)),
  );
  const nbFilles = mode_sans_outil
    ? (nb_filles_force ?? posesLaizeGeom)
    : posesLaizeGeom;

  const pasDev = dev_mm + INTERVALLE_DEV_MM;
  const posesDev = mode_sans_outil
    ? 1
    : cylindreDeveloppe
      ? Math.max(1, nbPosesDev(cylindreDeveloppe, pasDev))
      : 1;
  const nbPoses = posesDev * nbFilles;

  const laizePlaque =
    laize_mm * nbFilles + INTERVALLE_LAIZE_MM * Math.max(0, nbFilles - 1);
  const laizeStock = laize_stock_mm ?? laizePlaque;
  const dechetLateral = mode_sans_outil
    ? Math.max(0, laizeStock - laizePlaque)
    : 0;

  // ml de matière (mock) : quantité × pas dev / poses, en mètres.
  const mlTotal = (quantite * pasDev) / Math.max(1, nbPoses) / 1000;

  // Ø bobine (mock géométrique simple).
  const epaisseurMm = (input.epaisseur_um ?? 150) / 1000;
  const rMandrin = mandrin_mm / 2;
  const surfaceMatiereMm2 = mlTotal * 1000 * epaisseurMm;
  const diametreBobine = Math.round(
    2 * Math.sqrt(rMandrin * rMandrin + surfaceMatiereMm2 / Math.PI),
  );

  // ── Coûts (MOCK) ────────────────────────────────────────────────
  const laizePapier = mode_sans_outil ? laizeStock : laizePlaque;
  const surfaceM2 = (mlTotal * laizePapier) / 1000;
  const coutMatiere = surfaceM2 * PRIX_M2_DEFAUT_EUR;
  const coutEncres = nb_couleurs * (0.012 * (quantite / 1000) + 8);
  const coutOutillage = mode_sans_outil ? 0 : 45 * Math.max(1, nbFilles);
  const coutFinitions = finitions.reduce(
    (acc, code) => acc + optionDelta(code, quantite) * (1 - MARGE_DEFAUT_PCT),
    0,
  );
  const coutFixe = 180; // calage mock
  const coutRevient =
    coutMatiere + coutEncres + coutOutillage + coutFinitions + coutFixe;
  const prixTotal = coutRevient / (1 - MARGE_DEFAUT_PCT);
  const prix1000 = (prixTotal / quantite) * 1000;

  const decompo: DevisPreviewDecompoLigne[] = [
    { poste: "Matière", montant: round2(coutMatiere) },
    { poste: "Encres", montant: round2(coutEncres) },
  ];
  if (!mode_sans_outil) {
    decompo.push({ poste: "Outillage", montant: round2(coutOutillage) });
  }
  if (finitions.length > 0) {
    decompo.push({ poste: "Finitions", montant: round2(coutFinitions) });
  }
  decompo.push({ poste: "Calage & fixes", montant: round2(coutFixe) });

  const options: DevisPreviewOptionCout[] = finitions.map((code) => ({
    code,
    delta_eur: optionDelta(code, quantite),
  }));
  const couleurPlus = round2(
    (0.012 * (quantite / 1000) + 8) / (1 - MARGE_DEFAUT_PCT),
  );

  // ── Alertes douces ──────────────────────────────────────────────
  if (matiere_id === null) {
    alertes.push({
      niveau: "info",
      message: "Choisis une matière pour affiner le prix.",
    });
  }
  if (!mode_sans_outil && cylindre_id === null) {
    alertes.push({
      niveau: "info",
      message: "Choisis un cylindre compatible pour figer la pose.",
    });
  }
  if (mode_sans_outil && laize_stock_mm === null) {
    alertes.push({
      niveau: "attention",
      message: "Renseigne la laize bobine stock pour calculer la refente.",
    });
  }
  if (mode_sans_outil && laizeStock > 0 && dechetLateral / laizeStock > 0.15) {
    alertes.push({
      niveau: "attention",
      message: `Déchet latéral élevé (${round1(dechetLateral)} mm) : une autre laize stock réduirait la perte.`,
    });
  }

  return {
    prix_ht: round2(prixTotal),
    cout_revient: round2(coutRevient),
    marge_pct: MARGE_DEFAUT_PCT,
    prix_1000: round2(prix1000),
    geometrie: {
      diametre_mm: diametreBobine,
      nb_poses: nbPoses,
      nb_filles: nbFilles,
      dechet_lateral_mm: round1(dechetLateral),
    },
    decompo,
    options,
    couleur_plus: couleurPlus,
    alertes,
  };
}

/** Point d'entrée « preview live » — MOCK async (mime un fetch réseau,
 * honore l'AbortSignal). Au swap : remplacer le corps par
 * `apiFetch<DevisPreviewResult>("/api/devis/preview", { method: "POST",
 *  body: JSON.stringify(input), signal: opts?.signal })`. Le reste est inchangé. */
export async function previewDevisLive(
  input: DevisPreviewInput,
  opts: DevisPreviewMockCtx & { signal?: AbortSignal } = {},
): Promise<DevisPreviewResult> {
  if (opts.signal?.aborted) {
    throw new DOMException("Aborted", "AbortError");
  }
  return computeDevisPreview(input, {
    cylindre_developpe_mm: opts.cylindre_developpe_mm,
  });
}
