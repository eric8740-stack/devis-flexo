import { describe, it, expect } from "vitest";

import type { DevisDetail } from "@/lib/api";

import {
  extractBriefClientFromDevis,
  mergeBriefClient,
} from "./store-helpers";
import { BRIEF_CLIENT_DEFAULTS } from "./types";

// Sprint 14 Lot 4.2 — tests sur les helpers purs du store briefClient.
// La logique React (Provider + useState) n'est pas testée ici (pas de
// `@testing-library/react`) ; on s'assure plutôt que les fonctions
// pures qui sous-tendent setBriefClient et hydrateFromDevisExistant
// se comportent correctement, y compris sur les edge cases.

const DEVIS_BASE: DevisDetail = {
  id: 42,
  numero: "DEV-2026-0042",
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

describe("BRIEF_CLIENT_DEFAULTS — defaults alignés backend", () => {
  it("a nb_fronts_sortie=1 et type_entree_fichier='a_designer'", () => {
    expect(BRIEF_CLIENT_DEFAULTS.nb_fronts_sortie).toBe(1);
    expect(BRIEF_CLIENT_DEFAULTS.type_entree_fichier).toBe("a_designer");
  });

  it("a nb_etiquettes_par_rouleau et diametre_max_bobine_mm à null", () => {
    expect(BRIEF_CLIENT_DEFAULTS.nb_etiquettes_par_rouleau).toBeNull();
    expect(BRIEF_CLIENT_DEFAULTS.diametre_max_bobine_mm).toBeNull();
  });

  it("a conditions_stockage avec lieu='interieur' par défaut", () => {
    expect(BRIEF_CLIENT_DEFAULTS.conditions_stockage.lieu).toBe("interieur");
  });
});

describe("mergeBriefClient — partial update", () => {
  it("merge un champ racine sans toucher aux autres", () => {
    const next = mergeBriefClient(BRIEF_CLIENT_DEFAULTS, {
      nb_fronts_sortie: 3,
    });
    expect(next.nb_fronts_sortie).toBe(3);
    expect(next.type_entree_fichier).toBe("a_designer");
    expect(next.conditions_stockage).toEqual(
      BRIEF_CLIENT_DEFAULTS.conditions_stockage,
    );
  });

  it("merge profond sur conditions_stockage (preserve les autres clés)", () => {
    const next = mergeBriefClient(BRIEF_CLIENT_DEFAULTS, {
      conditions_stockage: { humidite_pct: 80 },
    });
    expect(next.conditions_stockage.humidite_pct).toBe(80);
    expect(next.conditions_stockage.lieu).toBe("interieur");
    expect(next.conditions_stockage.t_min_c).toBeNull();
  });

  it("change le type_entree_fichier sans affecter le reste", () => {
    const next = mergeBriefClient(BRIEF_CLIENT_DEFAULTS, {
      type_entree_fichier: "vierge",
    });
    expect(next.type_entree_fichier).toBe("vierge");
    expect(next.nb_fronts_sortie).toBe(1);
  });
});

describe("extractBriefClientFromDevis — hydratation depuis DevisDetail", () => {
  it("restaure les 5 champs quand le devis est entièrement renseigné", () => {
    const devis: DevisDetail = {
      ...DEVIS_BASE,
      nb_etiquettes_par_rouleau: 2000,
      diametre_max_bobine_mm: 250,
      nb_fronts_sortie: 4,
      type_entree_fichier: "bat_pro_fourni",
      conditions_stockage: {
        humidite_pct: 85,
        t_min_c: -5,
        t_max_c: 70,
        lieu: "exterieur",
      },
    };
    expect(extractBriefClientFromDevis(devis)).toEqual({
      nb_etiquettes_par_rouleau: 2000,
      diametre_max_bobine_mm: 250,
      nb_fronts_sortie: 4,
      type_entree_fichier: "bat_pro_fourni",
      conditions_stockage: {
        humidite_pct: 85,
        t_min_c: -5,
        t_max_c: 70,
        lieu: "exterieur",
      },
    });
  });

  it("applique les defaults backend si les champs sont undefined", () => {
    const result = extractBriefClientFromDevis(DEVIS_BASE);
    expect(result.nb_fronts_sortie).toBe(1);
    expect(result.type_entree_fichier).toBe("a_designer");
    expect(result.nb_etiquettes_par_rouleau).toBeNull();
    expect(result.diametre_max_bobine_mm).toBeNull();
    expect(result.conditions_stockage).toEqual(
      BRIEF_CLIENT_DEFAULTS.conditions_stockage,
    );
  });

  it("conserve null sur les champs stockage absents (partial)", () => {
    const devis: DevisDetail = {
      ...DEVIS_BASE,
      conditions_stockage: { humidite_pct: 60 },
    };
    const result = extractBriefClientFromDevis(devis);
    expect(result.conditions_stockage.humidite_pct).toBe(60);
    expect(result.conditions_stockage.t_min_c).toBeNull();
    expect(result.conditions_stockage.t_max_c).toBeNull();
    expect(result.conditions_stockage.lieu).toBe("interieur");
  });
});
