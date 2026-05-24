import { describe, expect, it } from "vitest";

import type { DevisDetail } from "./api";
import {
  NON_RENSEIGNE,
  briefClientEstVide,
  formatLieu,
  formatMmOrTiret,
  formatNbOrTiret,
  formatPourcentOrTiret,
  formatTemperatureOrTiret,
  formatTypeEntree,
} from "./brief-client-display";

// Sprint 14 Lot 4.6 — tests des helpers d'affichage lecture seule.

const DEVIS_VIDE: DevisDetail = {
  id: 1,
  numero: "DEV-2026-0001",
  date_creation: "2026-05-20T00:00:00",
  date_modification: "2026-05-20T00:00:00",
  statut: "brouillon",
  client_id: null,
  client_nom: null,
  machine_id: 1,
  machine_nom: "MA-1",
  payload_input: {},
  payload_output: {},
  mode_calcul: "manuel",
  cylindre_choisi_z: null,
  cylindre_choisi_nb_etiq: null,
  format_h_mm: "80",
  format_l_mm: "100",
  ht_total_eur: "0",
};

describe("formatNbOrTiret", () => {
  it("retourne 'Non renseigné' pour null/undefined", () => {
    expect(formatNbOrTiret(null)).toBe(NON_RENSEIGNE);
    expect(formatNbOrTiret(undefined)).toBe(NON_RENSEIGNE);
  });

  it("retourne la valeur formatée fr-FR (espace insécable séparateur milliers)", () => {
    // Note : toLocaleString fr-FR utilise un espace insécable (  ou \xa0)
    expect(formatNbOrTiret(1500)).toMatch(/1.500/);
  });
});

describe("formatMmOrTiret", () => {
  it("retourne 'Non renseigné' si null", () => {
    expect(formatMmOrTiret(null)).toBe(NON_RENSEIGNE);
  });

  it("ajoute le suffixe ' mm'", () => {
    expect(formatMmOrTiret(220)).toMatch(/220.*mm$/);
  });
});

describe("formatTypeEntree", () => {
  it("traduit les 3 valeurs Literal en labels lisibles", () => {
    expect(formatTypeEntree("vierge")).toBe("Rouleau vierge");
    expect(formatTypeEntree("bat_pro_fourni")).toBe(
      "BAT / PDF fourni par le client",
    );
    expect(formatTypeEntree("a_designer")).toBe("À concevoir");
  });

  it("retourne 'Non renseigné' pour valeur absente", () => {
    expect(formatTypeEntree(null)).toBe(NON_RENSEIGNE);
    expect(formatTypeEntree(undefined)).toBe(NON_RENSEIGNE);
  });

  it("retourne la valeur brute si inconnue (forward-compat)", () => {
    expect(formatTypeEntree("nouveau_type_S15")).toBe("nouveau_type_S15");
  });
});

describe("formatLieu", () => {
  it("traduit interieur/exterieur en labels", () => {
    expect(formatLieu("interieur")).toBe("Intérieur");
    expect(formatLieu("exterieur")).toBe("Extérieur");
  });

  it("retourne 'Non renseigné' si null/empty", () => {
    expect(formatLieu(null)).toBe(NON_RENSEIGNE);
    expect(formatLieu("")).toBe(NON_RENSEIGNE);
  });
});

describe("formatPourcentOrTiret + formatTemperatureOrTiret", () => {
  it("ajoute les suffixes corrects", () => {
    expect(formatPourcentOrTiret(80)).toMatch(/80.*%$/);
    expect(formatTemperatureOrTiret(-5)).toMatch(/-5.*°C$/);
    expect(formatTemperatureOrTiret(40)).toMatch(/40.*°C$/);
  });

  it("zéro est une valeur valide (pas confondu avec absent)", () => {
    expect(formatPourcentOrTiret(0)).toMatch(/0.*%$/);
    expect(formatTemperatureOrTiret(0)).toMatch(/0.*°C$/);
  });
});

describe("briefClientEstVide", () => {
  it("retourne true pour un devis sans aucun champ brief client", () => {
    expect(briefClientEstVide(DEVIS_VIDE)).toBe(true);
  });

  it("retourne true si seuls les server_default sont présents", () => {
    const devis: DevisDetail = {
      ...DEVIS_VIDE,
      nb_fronts_sortie: 1,
      type_entree_fichier: "a_designer",
    };
    expect(briefClientEstVide(devis)).toBe(true);
  });

  it("retourne false dès qu'un champ optionnel est renseigné", () => {
    expect(
      briefClientEstVide({
        ...DEVIS_VIDE,
        nb_etiquettes_par_rouleau: 1500,
      }),
    ).toBe(false);
  });

  it("retourne false si conditions_stockage est posé", () => {
    expect(
      briefClientEstVide({
        ...DEVIS_VIDE,
        conditions_stockage: { humidite_pct: 80 },
      }),
    ).toBe(false);
  });

  it("retourne false si type_entree_fichier diffère du default", () => {
    expect(
      briefClientEstVide({
        ...DEVIS_VIDE,
        type_entree_fichier: "bat_pro_fourni",
      }),
    ).toBe(false);
  });
});
