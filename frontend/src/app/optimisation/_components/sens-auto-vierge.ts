import type { SensEnroulement } from "@/lib/api";

import type { TypeEntreeFichier } from "./brief-client/types";

/**
 * Auto-sélection du sens d'enroulement selon le type d'entrée fichier.
 *
 * Règle métier : « rouleau vierge » = bobine livrée non imprimée → SE0 (face
 * extérieur, sans impression) ou SE9 (face intérieur, sans impression). Quand
 * l'utilisateur passe en `type_entree_fichier = "vierge"`, on remappe le sens
 * courant vers son équivalent SE0/SE9 en conservant la face (Ext/Int) qu'il
 * avait avant. Quand il en sort (BAT fourni / à concevoir), on remappe
 * SE0→SE1 et SE9→SE5 (sens par défaut avec impression sur la même face).
 *
 * Volontairement PAS de verrouillage : après l'auto-sélection, l'utilisateur
 * peut toujours cliquer manuellement un autre sens (cf. brief).
 *
 * Note : le brief évoquait un champ `lieu_de_stockage` Intérieur/Extérieur,
 * qui n'existe pas dans le modèle. La face est dérivée du sens courant —
 * SE1-4 + SE0 = ext, SE5-8 + SE9 = int (cf. SE_OPTIONS dans optimisation
 * page.tsx).
 */
const SENS_FACE_EXT: ReadonlySet<SensEnroulement> = new Set<SensEnroulement>([
  "SE0",
  "SE1",
  "SE2",
  "SE3",
  "SE4",
]);

export function sensAutoForTypeEntree(
  currentSens: SensEnroulement,
  typeEntree: TypeEntreeFichier,
): SensEnroulement {
  if (typeEntree === "vierge") {
    // SE0/SE9 : déjà sur le sens "vierge" de la bonne face → inchangé.
    if (currentSens === "SE0" || currentSens === "SE9") return currentSens;
    return SENS_FACE_EXT.has(currentSens) ? "SE0" : "SE9";
  }
  // Hors mode vierge : remap les sens "sans impression" vers leur équivalent
  // imprimable par défaut sur la même face.
  if (currentSens === "SE0") return "SE1";
  if (currentSens === "SE9") return "SE5";
  return currentSens;
}
