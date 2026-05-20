// Sprint 14 Lot 3 — règle UI locale (MVP) qui suggère un type d'adhésif
// à partir des conditions de stockage saisies dans le brief client. Pas
// d'appel backend : c'est de l'aide à la décision affichée inline. La
// règle pourra migrer côté moteur si elle se complexifie.

export interface ConditionsStockage {
  humidite_pct?: number | null;
  t_min_c?: number | null;
  t_max_c?: number | null;
  lieu?: "interieur" | "exterieur" | string | null;
}

const CONSEIL_STANDARD = "Adhésif permanent standard";

/**
 * Retourne la liste des conseils adhésif applicables.
 * Les critères se cumulent — si plusieurs s'appliquent, on les affiche
 * tous. Si aucun critère ne déclenche, on renvoie le conseil standard.
 * Seuils stricts (`>`, `<`) — la valeur de bord ne déclenche pas.
 */
export function conseilsAdhesif(
  conditions: ConditionsStockage | null | undefined
): string[] {
  if (!conditions) return [CONSEIL_STANDARD];

  const conseils: string[] = [];

  if (
    typeof conditions.humidite_pct === "number" &&
    conditions.humidite_pct > 70
  ) {
    conseils.push("Privilégier adhésif tropical (résistance humidité)");
  }
  if (typeof conditions.t_min_c === "number" && conditions.t_min_c < 0) {
    conseils.push("Adhésif froid négatif requis");
  }
  if (typeof conditions.t_max_c === "number" && conditions.t_max_c > 60) {
    conseils.push("Adhésif haute température (cuisson, four)");
  }
  if (conditions.lieu === "exterieur") {
    conseils.push("Adhésif UV-résistant");
  }

  return conseils.length > 0 ? conseils : [CONSEIL_STANDARD];
}
