import type { DevisCreate, DevisDetail } from "@/lib/api";

import { BRIEF_CLIENT_DEFAULTS, type BriefClientData } from "./types";

// Type utilitaire : projection des 5 champs brief client dans le shape
// attendu par DevisCreate / DevisUpdate (sous-champs non nullables côté
// types TS Lot 4.1). Extrait de DevisCreate via Pick pour rester aligné.
type BriefClientPayload = Pick<
  DevisCreate,
  | "nb_etiquettes_par_rouleau"
  | "diametre_max_bobine_mm"
  | "nb_fronts_sortie"
  | "type_entree_fichier"
  | "conditions_stockage"
>;

// Sprint 14 Lot 4.2 — logique pure du brief client extraite du store
// React pour rester testable sans @testing-library/react. Le Provider
// délègue ces fonctions, ce qui isole la logique métier des hooks.

/**
 * Applique un patch partiel sur le state briefClient courant. Le merge
 * est shallow sur le niveau racine, et profond pour `conditions_stockage`
 * (sinon un patch `{ conditions_stockage: { humidite_pct: 80 } }` effacerait
 * les autres champs de stockage).
 */
export function mergeBriefClient(
  current: BriefClientData,
  patch: Partial<BriefClientData>,
): BriefClientData {
  return {
    ...current,
    ...patch,
    conditions_stockage: patch.conditions_stockage
      ? {
          ...current.conditions_stockage,
          ...patch.conditions_stockage,
        }
      : current.conditions_stockage,
  };
}

/**
 * Reconstruit un `BriefClientData` complet depuis un `DevisDetail`
 * chargé en mode édition. Les defaults backend Sprint 14 Lot 1
 * (`nb_fronts_sortie=1`, `type_entree_fichier="a_designer"`) sont
 * appliqués si le champ est null/undefined côté API.
 */
export function extractBriefClientFromDevis(
  devis: DevisDetail,
): BriefClientData {
  const stockageApi = devis.conditions_stockage;
  const stockageDefaut = BRIEF_CLIENT_DEFAULTS.conditions_stockage;
  return {
    nb_etiquettes_par_rouleau: devis.nb_etiquettes_par_rouleau ?? null,
    diametre_max_bobine_mm: devis.diametre_max_bobine_mm ?? null,
    nb_fronts_sortie: devis.nb_fronts_sortie ?? 1,
    type_entree_fichier: devis.type_entree_fichier ?? "a_designer",
    conditions_stockage: stockageApi
      ? {
          humidite_pct: stockageApi.humidite_pct ?? null,
          t_min_c: stockageApi.t_min_c ?? null,
          t_max_c: stockageApi.t_max_c ?? null,
          lieu: stockageApi.lieu ?? stockageDefaut.lieu ?? "interieur",
        }
      : { ...stockageDefaut },
  };
}

/**
 * Projette `BriefClientData` (state UI, valeurs internes nullable) vers
 * le shape `DevisCreate`/`DevisUpdate` (sous-champs `conditions_stockage`
 * non-nullable). Les valeurs `null` sont omises ; si tout est `null`,
 * `conditions_stockage` vaut `null` (préserve la sémantique « pas de
 * conditions saisies » côté backend).
 */
export function briefClientToPayload(b: BriefClientData): BriefClientPayload {
  const s = b.conditions_stockage;
  const stockage: NonNullable<BriefClientPayload["conditions_stockage"]> = {};
  if (s.humidite_pct != null) stockage.humidite_pct = s.humidite_pct;
  if (s.t_min_c != null) stockage.t_min_c = s.t_min_c;
  if (s.t_max_c != null) stockage.t_max_c = s.t_max_c;
  if (s.lieu) stockage.lieu = s.lieu;

  return {
    nb_etiquettes_par_rouleau: b.nb_etiquettes_par_rouleau,
    diametre_max_bobine_mm: b.diametre_max_bobine_mm,
    nb_fronts_sortie: b.nb_fronts_sortie,
    type_entree_fichier: b.type_entree_fichier,
    conditions_stockage:
      Object.keys(stockage).length > 0 ? stockage : null,
  };
}
