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
    forme: null,
    quantite: 10000,
    nb_couleurs: 4,
    cylindre_id: 1,
    machine_id: 1,
    matiere_id: 1,
    epaisseur_um: 150,
    mandrin_mm: 76,
    diam_max_mm: null,
    nb_filles_force: null,
    mode_sans_outil: false,
    laize_stock_mm: null,
    finitions: [],
    ...over,
  };
}

describe("devisPreviewMock — compute déterministe (contrat final)", () => {
  it("inputs incomplets → prix 0 + alerte bloquante (jamais de faux prix)", () => {
    const r = computeDevisPreview(baseInput({ laize_mm: 0 }));
    expect(r.prix_ht).toBe(0);
    expect(r.alertes.some((a) => a.niveau === "bloquant")).toBe(true);
  });

  it("inputs valides (avec outil) → prix>0, €/1000>0, poses≥1, pas de refente", () => {
    const r = computeDevisPreview(baseInput(), { cylindre_developpe_mm: 330 });
    expect(r.prix_ht).toBeGreaterThan(0);
    expect(r.prix_1000).toBeGreaterThan(0);
    expect(r.marge_pct).toBeGreaterThan(0);
    expect(r.geometrie.nb_poses).toBeGreaterThanOrEqual(1);
    // Avec outil : pas de déchet de refente.
    expect(r.geometrie.dechet_lateral_mm).toBe(0);
    // Décompo = postes de coût (poste/montant).
    expect(r.decompo.length).toBeGreaterThan(0);
    expect(r.decompo.every((l) => typeof l.montant === "number")).toBe(true);
  });

  it("€/1000 cohérent avec prix_ht / quantité", () => {
    const r = computeDevisPreview(baseInput({ quantite: 5000 }), {
      cylindre_developpe_mm: 330,
    });
    expect(r.prix_1000).toBeCloseTo((r.prix_ht / 5000) * 1000, 1);
  });

  it("mode sans outil → déchet latéral + nb_filles dans geometrie", () => {
    const r = computeDevisPreview(
      baseInput({
        mode_sans_outil: true,
        laize_stock_mm: 330,
        cylindre_id: null,
        machine_id: null,
      }),
    );
    expect(r.geometrie.dechet_lateral_mm).toBeGreaterThanOrEqual(0);
    expect(r.geometrie.nb_filles).toBeGreaterThanOrEqual(1);
    // Pas de poste outillage en sans outil.
    expect(r.decompo.some((l) => l.poste === "Outillage")).toBe(false);
  });

  it("nb_filles_force respecté en sans outil", () => {
    const r = computeDevisPreview(
      baseInput({
        mode_sans_outil: true,
        laize_stock_mm: 330,
        nb_filles_force: 2,
      }),
    );
    expect(r.geometrie.nb_filles).toBe(2);
  });

  it("finitions → un coût marginal par option (delta_eur>0) + couleur_plus", () => {
    const r = computeDevisPreview(baseInput({ finitions: ["VERNIS", "DORURE"] }), {
      cylindre_developpe_mm: 330,
    });
    expect(r.options.map((o) => o.code)).toEqual(["VERNIS", "DORURE"]);
    expect(r.options.every((o) => o.delta_eur > 0)).toBe(true);
    expect(r.couleur_plus).toBeGreaterThan(0);
  });

  it("matière absente → alerte info (état partiel toléré)", () => {
    const r = computeDevisPreview(baseInput({ matiere_id: null }), {
      cylindre_developpe_mm: 330,
    });
    expect(r.alertes.some((a) => a.niveau === "info")).toBe(true);
    // Le prix reste estimé malgré la matière manquante.
    expect(r.prix_ht).toBeGreaterThan(0);
  });

  it("déterministe : mêmes entrées → mêmes sorties", () => {
    const ctx = { cylindre_developpe_mm: 330 };
    expect(computeDevisPreview(baseInput(), ctx)).toEqual(
      computeDevisPreview(baseInput(), ctx),
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
