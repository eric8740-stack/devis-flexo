import type { DevisDetail } from "./api";

// Sprint 14 Lot 4.6 — helpers d'affichage lecture seule du brief client.
// Utilisés par `EditMultiLotsPanel` (page édition devis multi-lots) et
// potentiellement d'autres écrans futurs (page détail, exports PDF).

const TYPE_ENTREE_LABELS: Record<string, string> = {
  vierge: "Rouleau vierge",
  bat_pro_fourni: "BAT / PDF fourni par le client",
  a_designer: "À concevoir",
};

const LIEU_LABELS: Record<string, string> = {
  interieur: "Intérieur",
  exterieur: "Extérieur",
};

export const NON_RENSEIGNE = "Non renseigné";

export function formatNbOrTiret(n: number | null | undefined): string {
  if (n === null || n === undefined) return NON_RENSEIGNE;
  return n.toLocaleString("fr-FR");
}

export function formatMmOrTiret(n: number | null | undefined): string {
  if (n === null || n === undefined) return NON_RENSEIGNE;
  return `${n.toLocaleString("fr-FR")} mm`;
}

export function formatTypeEntree(t: string | null | undefined): string {
  if (!t) return NON_RENSEIGNE;
  return TYPE_ENTREE_LABELS[t] ?? t;
}

export function formatLieu(lieu: string | null | undefined): string {
  if (!lieu) return NON_RENSEIGNE;
  return LIEU_LABELS[lieu] ?? lieu;
}

export function formatPourcentOrTiret(n: number | null | undefined): string {
  if (n === null || n === undefined) return NON_RENSEIGNE;
  return `${n.toLocaleString("fr-FR")} %`;
}

export function formatTemperatureOrTiret(
  n: number | null | undefined,
): string {
  if (n === null || n === undefined) return NON_RENSEIGNE;
  return `${n.toLocaleString("fr-FR")} °C`;
}

/**
 * Renvoie `true` si le devis n'a aucun champ brief client renseigné
 * (cas d'un devis pré-S14 où tous les colonnes sont null ou aux defaults
 * backend serveur_default. Utilisé pour afficher une mention "non saisi
 * pour ce devis" plutôt qu'un bloc vide.
 */
export function briefClientEstVide(devis: DevisDetail): boolean {
  return (
    devis.nb_etiquettes_par_rouleau == null &&
    devis.diametre_max_bobine_mm == null &&
    devis.conditions_stockage == null &&
    // nb_fronts_sortie=1 et type_entree_fichier='a_designer' sont les
    // server_default — on considère que le brief est "vide" si pas
    // d'autres champs renseignés en plus.
    (devis.nb_fronts_sortie === 1 || devis.nb_fronts_sortie == null) &&
    (devis.type_entree_fichier === "a_designer" ||
      devis.type_entree_fichier == null)
  );
}
