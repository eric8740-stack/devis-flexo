import type { DevisDetail } from "@/lib/api";

import { BRIEF_CLIENT_DEFAULTS, type BriefClientData } from "./types";

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
