// Lot front — devis page unique réactive.
//
// ⚠️ MOCK du contrat « live preview » tant que l'endpoint backend CC1
// `POST /api/devis/preview` n'est pas mergé. Tout est ISOLÉ ici : quand
// l'endpoint existe, on remplace `previewDevisLive` par un `apiFetch` sans
// toucher l'UI (l'interface `DevisPreviewResult` est le contrat cible).
//
// Le calcul est une APPROXIMATION déterministe (pas le cost_engine sacré) :
// il sert UNIQUEMENT à rendre la page réactive en démo (hero prix + décompo
// + indices dérivés). Les vrais chiffres viendront du backend.

import type { CylindreParc } from "@/lib/api";

export interface DevisPreviewInput {
  laize_mm: number;
  dev_mm: number;
  quantite: number;
  nb_couleurs: number;
  // Mode « format sans outil » (impression pleine largeur + refente).
  mode_sans_outil: boolean;
  laize_stock_mm: number | null;
  nb_filles_force: number | null;
  // Outil : cylindre choisi (null en sans outil).
  cylindre_id: number | null;
  cylindre_developpe_mm: number | null;
  // Matière.
  matiere_prix_m2_eur: number | null;
  epaisseur_um: number | null;
  // Bobinage.
  mandrin_mm: number;
  diametre_max_bobine_mm: number | null;
  // Finitions.
  nb_options: number;
  // Commercial.
  bord_lateral_mm: number;
}

export interface DevisPreviewDecompo {
  laize_plaque_mm: number;
  bord_lateral_mm: number;
  laize_papier_mm: number;
  // Sans outil uniquement (null sinon).
  laize_stock_mm: number | null;
  laize_utile_mm: number | null;
  dechet_lateral_mm: number | null;
  nb_filles: number | null;
}

export interface DevisPreviewDerived {
  nb_poses_dev: number;
  nb_poses_laize: number;
  diametre_bobine_mm: number;
  ml_total: number;
}

export interface DevisPreviewResult {
  prix_total_ht_eur: number;
  marge_pct: number;
  cout_revient_eur: number;
  decompo: DevisPreviewDecompo;
  derived: DevisPreviewDerived;
  // null = preview OK ; sinon message (ex. champs insuffisants). Le hero
  // affiche le message au lieu d'un prix (jamais « 0,00 € » trompeur).
  incomplet: string | null;
}

const PAS_CHENILLE_MM = 3.175; // 1 dent flexo
const MARGE_DEFAUT_PCT = 0.3; // mock (le vrai vient de ConfigCouts)

/** Un cylindre est « compatible » avec le format si son développé permet
 * au moins une pose en dev (développé ≥ dev + intervalle). Filtre purement
 * géométrique côté front pour alimenter le select Outil. */
export function cylindresCompatibles(
  cylindres: CylindreParc[],
  devMm: number,
  intervalleDevMm: number,
): CylindreParc[] {
  const pas = devMm + intervalleDevMm;
  if (pas <= 0) return cylindres;
  return cylindres.filter((c) => parseFloat(c.developpe_mm) >= pas);
}

function nbPosesDev(developpeMm: number, pasDevMm: number): number {
  if (pasDevMm <= 0 || developpeMm < pasDevMm) return 0;
  return Math.floor(developpeMm / pasDevMm);
}

/** Approximation déterministe du devis pour la preview live (MOCK). */
export function computeDevisPreview(
  input: DevisPreviewInput,
): DevisPreviewResult {
  const {
    laize_mm,
    dev_mm,
    quantite,
    nb_couleurs,
    mode_sans_outil,
    laize_stock_mm,
    nb_filles_force,
    cylindre_developpe_mm,
    matiere_prix_m2_eur,
    mandrin_mm,
    nb_options,
    bord_lateral_mm,
  } = input;

  if (!(laize_mm > 0) || !(dev_mm > 0) || !(quantite > 0)) {
    return {
      prix_total_ht_eur: 0,
      marge_pct: MARGE_DEFAUT_PCT,
      cout_revient_eur: 0,
      decompo: {
        laize_plaque_mm: 0,
        bord_lateral_mm,
        laize_papier_mm: 0,
        laize_stock_mm: null,
        laize_utile_mm: null,
        dechet_lateral_mm: null,
        nb_filles: null,
      },
      derived: {
        nb_poses_dev: 0,
        nb_poses_laize: 0,
        diametre_bobine_mm: 0,
        ml_total: 0,
      },
      incomplet: "Renseigne laize, développé et quantité pour estimer le prix.",
    };
  }

  const intervalleLaize = bord_lateral_mm > 0 ? 3 : 3; // mock : pas latéral
  // Poses laize = combien d'étiquettes (ou bobines filles) en largeur.
  const laizeUtilePresse = laize_stock_mm ?? 330;
  const posesLaizeGeom = Math.max(
    1,
    Math.floor(laizeUtilePresse / (laize_mm + intervalleLaize)),
  );
  const nbFilles = mode_sans_outil
    ? (nb_filles_force ?? posesLaizeGeom)
    : posesLaizeGeom;

  // Poses dev = depuis le cylindre choisi (avec outil) sinon impression
  // continue (1 « pose » conceptuelle pour le mock).
  const pasDev = dev_mm + 2; // mock intervalle dev
  const posesDev = mode_sans_outil
    ? 1
    : cylindre_developpe_mm
      ? Math.max(1, nbPosesDev(cylindre_developpe_mm, pasDev))
      : 1;

  const laizePlaque = laize_mm * nbFilles + intervalleLaize * (nbFilles - 1);
  const laizePapierAvecOutil = laizePlaque + 2 * bord_lateral_mm;
  const laizeStock = laize_stock_mm ?? laizePapierAvecOutil;
  const laizePapier = mode_sans_outil ? laizeStock : laizePapierAvecOutil;

  // ml de matière (mock) : quantité × pas dev / poses, en mètres.
  const mlTotal = (quantite * pasDev) / Math.max(1, posesDev * nbFilles) / 1000;
  const surfaceM2 = (mlTotal * laizePapier) / 1000;
  const prixM2 = matiere_prix_m2_eur ?? 0.35;

  // Coût de revient (MOCK) = matière + encres + outillage + options.
  const coutMatiere = surfaceM2 * prixM2;
  const coutEncres = nb_couleurs * 0.012 * (quantite / 1000);
  const coutOutillage = mode_sans_outil ? 0 : 45 * Math.max(1, nbFilles);
  const coutOptions = nb_options * 25;
  const coutFixe = 180; // calage mock
  const coutRevient =
    coutMatiere + coutEncres + coutOutillage + coutOptions + coutFixe;
  const prixTotal = coutRevient / (1 - MARGE_DEFAUT_PCT);

  const dechetLateral = mode_sans_outil
    ? Math.max(0, laizeStock - laizePlaque)
    : null;

  // Ø bobine (mock géométrique simple).
  const epaisseurMm = (input.epaisseur_um ?? 150) / 1000;
  const rMandrin = mandrin_mm / 2;
  const surfaceMatiereMm2 = mlTotal * 1000 * epaisseurMm;
  const diametreBobine = Math.round(
    2 * Math.sqrt(rMandrin * rMandrin + surfaceMatiereMm2 / Math.PI),
  );

  const round2 = (n: number) => Math.round(n * 100) / 100;
  const round1 = (n: number) => Math.round(n * 10) / 10;

  return {
    prix_total_ht_eur: round2(prixTotal),
    marge_pct: MARGE_DEFAUT_PCT,
    cout_revient_eur: round2(coutRevient),
    decompo: {
      laize_plaque_mm: round1(laizePlaque),
      bord_lateral_mm,
      laize_papier_mm: round1(laizePapier),
      laize_stock_mm: mode_sans_outil ? round1(laizeStock) : null,
      laize_utile_mm: mode_sans_outil ? round1(laizePlaque) : null,
      dechet_lateral_mm: dechetLateral != null ? round1(dechetLateral) : null,
      nb_filles: mode_sans_outil ? nbFilles : null,
    },
    derived: {
      nb_poses_dev: posesDev,
      nb_poses_laize: nbFilles,
      diametre_bobine_mm: diametreBobine,
      ml_total: round1(mlTotal),
    },
    incomplet: null,
  };
}

/** Point d'entrée « preview live » — MOCK async (mime un fetch réseau).
 * Remplacer le corps par `apiFetch<DevisPreviewResult>("/api/devis/preview", …)`
 * quand le back CC1 est mergé ; le reste de l'UI est inchangé. */
export async function previewDevisLive(
  input: DevisPreviewInput,
): Promise<DevisPreviewResult> {
  return computeDevisPreview(input);
}

export const PREVIEW_PAS_CHENILLE_MM = PAS_CHENILLE_MM;
