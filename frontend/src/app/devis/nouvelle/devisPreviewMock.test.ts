import { describe, expect, it } from "vitest";

import type { CylindreParc } from "@/lib/api";

import {
  computeDevisPreview,
  cylindresCompatibles,
  type DevisPreviewInput,
} from "./devisPreviewMock";

function baseInput(over: Partial<DevisPreviewInput> = {}): DevisPreviewInput {
  return {
    laize_mm: 100,
    dev_mm: 80,
    quantite: 10000,
    nb_couleurs: 4,
    mode_sans_outil: false,
    laize_stock_mm: null,
    nb_filles_force: null,
    cylindre_id: 1,
    cylindre_developpe_mm: 330,
    matiere_prix_m2_eur: null,
    epaisseur_um: 150,
    mandrin_mm: 76,
    diametre_max_bobine_mm: null,
    nb_options: 0,
    bord_lateral_mm: 10,
    ...over,
  };
}

describe("devisPreviewMock — compute déterministe", () => {
  it("inputs incomplets → message incomplet, prix 0 (jamais de faux prix)", () => {
    const r = computeDevisPreview(baseInput({ laize_mm: 0 }));
    expect(r.incomplet).toBeTruthy();
    expect(r.prix_total_ht_eur).toBe(0);
  });

  it("inputs valides (avec outil) → prix > 0, poses ≥ 1, pas de déchet refente", () => {
    const r = computeDevisPreview(baseInput());
    expect(r.incomplet).toBeNull();
    expect(r.prix_total_ht_eur).toBeGreaterThan(0);
    expect(r.derived.nb_poses_laize).toBeGreaterThanOrEqual(1);
    expect(r.derived.nb_poses_dev).toBeGreaterThanOrEqual(1);
    // Avec outil : pas de ligne refente.
    expect(r.decompo.dechet_lateral_mm).toBeNull();
    expect(r.decompo.nb_filles).toBeNull();
  });

  it("mode sans outil → déchet latéral (stock − utile) + nb_filles exposés", () => {
    const r = computeDevisPreview(
      baseInput({
        mode_sans_outil: true,
        laize_stock_mm: 330,
        cylindre_id: null,
        cylindre_developpe_mm: null,
      }),
    );
    expect(r.incomplet).toBeNull();
    expect(r.decompo.laize_stock_mm).toBe(330);
    expect(r.decompo.dechet_lateral_mm).not.toBeNull();
    expect(r.decompo.dechet_lateral_mm).toBeGreaterThanOrEqual(0);
    expect(r.decompo.nb_filles).toBeGreaterThanOrEqual(1);
  });

  it("nb_filles_force respecté en sans outil", () => {
    const r = computeDevisPreview(
      baseInput({
        mode_sans_outil: true,
        laize_stock_mm: 330,
        nb_filles_force: 2,
      }),
    );
    expect(r.decompo.nb_filles).toBe(2);
  });

  it("déterministe : mêmes entrées → mêmes sorties", () => {
    expect(computeDevisPreview(baseInput())).toEqual(
      computeDevisPreview(baseInput()),
    );
  });
});

describe("cylindresCompatibles — filtre par format", () => {
  const cyls: CylindreParc[] = [
    { id: 1, nb_dents: 104, developpe_mm: "330.20", actif: true, notes: null, date_creation: "" },
    { id: 2, nb_dents: 30, developpe_mm: "95.25", actif: true, notes: null, date_creation: "" },
    { id: 3, nb_dents: 20, developpe_mm: "63.50", actif: true, notes: null, date_creation: "" },
  ];

  it("garde les cylindres dont le développé tient le dev + intervalle", () => {
    // dev=80, intervalle=2 → pas=82 : 330 ✓, 95 ✓, 63 ✗
    const ok = cylindresCompatibles(cyls, 80, 2);
    expect(ok.map((c) => c.id)).toEqual([1, 2]);
  });

  it("dev plus grand → moins de cylindres", () => {
    const ok = cylindresCompatibles(cyls, 100, 2); // pas=102 : seul 330
    expect(ok.map((c) => c.id)).toEqual([1]);
  });
});
