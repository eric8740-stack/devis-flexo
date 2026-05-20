import type { ConditionsStockage } from "@/lib/adhesif-helper";

// Sprint 14 Lot 3 — types partagés des sous-sections du brief client.
// Centralisés ici pour qu'une évolution du contrat se limite à 1 fichier.

export type TypeEntreeFichier =
  | "vierge"
  | "bat_pro_fourni"
  | "a_designer";

export interface BriefClientData {
  nb_etiquettes_par_rouleau: number | null;
  diametre_max_bobine_mm: number | null;
  nb_fronts_sortie: number;
  type_entree_fichier: TypeEntreeFichier;
  conditions_stockage: ConditionsStockage;
}

export const BRIEF_CLIENT_DEFAULTS: BriefClientData = {
  nb_etiquettes_par_rouleau: null,
  diametre_max_bobine_mm: null,
  nb_fronts_sortie: 1,
  type_entree_fichier: "a_designer",
  conditions_stockage: {
    humidite_pct: null,
    t_min_c: null,
    t_max_c: null,
    lieu: "interieur",
  },
};

// Retourne null pour une chaîne vide, sinon le nombre parsé. Évite
// d'envoyer NaN/0 quand l'utilisateur efface le champ.
export function parseNumOrNull(v: string): number | null {
  if (v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function inputValueNum(v: number | null | undefined): string {
  return v === null || v === undefined ? "" : String(v);
}
