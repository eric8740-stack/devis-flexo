import { describe, expect, it } from "vitest";

import type { CylindreParc, DevisPreviewOut } from "@/lib/api";

import {
  buildPreviewRequest,
  cylindresCompatibles,
  parsePreview,
  posesPourPersist,
  type DevisPreviewInput,
} from "./devisPreview";

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
    options_codes: [],
    ...over,
  };
}

describe("buildPreviewRequest — état page → body wire", () => {
  it("mappe nb_couleurs en objet et passe la machine", () => {
    const r = buildPreviewRequest(baseInput({ options_codes: ["VERNIS"] }));
    expect(r.laize).toBe(100);
    expect(r.dev).toBe(80);
    expect(r.quantite).toBe(10000);
    expect(r.machine_id).toBe(1);
    expect(r.cylindre_id).toBe(1);
    expect(r.nb_couleurs).toEqual({
      impression: 4,
      pantone: 0,
      blanc: 0,
      vernis: 0,
    });
    // Options par CODE (#130) ; finitions ST ad-hoc inutilisées.
    expect(r.options_codes).toEqual(["VERNIS"]);
    expect(r.finitions).toEqual([]);
  });

  it("champs absents/invalides → null (le backend impose gt=0)", () => {
    const r = buildPreviewRequest(
      baseInput({ laize_mm: 0, quantite: 0, nb_couleurs: 0, epaisseur_um: 0 }),
    );
    expect(r.laize).toBeNull();
    expect(r.quantite).toBeNull();
    expect(r.nb_couleurs).toBeNull();
    expect(r.epaisseur_um).toBeNull();
  });

  it("sans outil → cylindre_id null mais machine conservée", () => {
    const r = buildPreviewRequest(
      baseInput({ mode_sans_outil: true, laize_stock_mm: 330 }),
    );
    expect(r.cylindre_id).toBeNull();
    expect(r.machine_id).toBe(1);
    expect(r.mode_sans_outil).toBe(true);
    expect(r.laize_stock_mm).toBe(330);
  });
});

describe("parsePreview — wire (Decimal en chaînes, nullable) → nombres", () => {
  it("parse les chaînes décimales et préserve les null", () => {
    const wire: DevisPreviewOut = {
      prix_ht: "123.45",
      cout_revient: "80.00",
      marge_pct: "30.00", // pourcentage, pas une fraction
      prix_1000: "12.35",
      geometrie: {
        diametre_mm: 250,
        nb_poses: 12,
        nb_filles: null,
        dechet_lateral_mm: null,
      },
      decompo: [
        { poste: "Matière", montant: "40.00" },
        { poste: "Encres", montant: "20.00" },
      ],
      options: [
        { code: "VERNIS", delta_eur: "12.00", impact_production: false },
        { code: "DORURE", delta_eur: null, impact_production: true },
        { code: "couleur_plus", delta_eur: "5.50", impact_production: false },
      ],
      alertes: [{ niveau: "info", message: "ok" }],
    };
    const r = parsePreview(wire);
    expect(r.prix_ht).toBe(123.45);
    expect(r.marge_pct).toBe(30);
    expect(r.geometrie.nb_filles).toBeNull();
    expect(r.decompo[0]).toEqual({ poste: "Matière", montant: 40 });
    expect(r.options[0]).toEqual({
      code: "VERNIS",
      delta_eur: 12,
      impact_production: false,
    });
    // Impact production sans forfait → delta null préservé + flag.
    expect(r.options[1]).toEqual({
      code: "DORURE",
      delta_eur: null,
      impact_production: true,
    });
    expect(r.alertes[0].niveau).toBe("info");
  });

  it("état trop partiel → prix null (jamais de faux 0 €)", () => {
    const wire: DevisPreviewOut = {
      prix_ht: null,
      cout_revient: null,
      marge_pct: null,
      prix_1000: null,
      geometrie: {
        diametre_mm: null,
        nb_poses: null,
        nb_filles: null,
        dechet_lateral_mm: null,
      },
      decompo: [],
      options: [],
      alertes: [{ niveau: "info", message: "Quantité manquante." }],
    };
    const r = parsePreview(wire);
    expect(r.prix_ht).toBeNull();
    expect(r.prix_1000).toBeNull();
    expect(r.decompo).toEqual([]);
  });
});

describe("posesPourPersist — géométrie best-effort pour le POST /devis", () => {
  it("avec outil : poses dev depuis le développé, poses laize depuis la laize", () => {
    // dev=80, intervalle 2 → 82 ; 330/82 = 4. laize=100, intervalle 3 → 103 ;
    // stock null → 330 ; 330/103 = 3.
    const r = posesPourPersist(baseInput(), 330);
    expect(r.nb_poses_dev).toBe(4);
    expect(r.nb_poses_laize).toBe(3);
  });

  it("sans outil : nb_filles_force prioritaire", () => {
    const r = posesPourPersist(
      baseInput({
        mode_sans_outil: true,
        laize_stock_mm: 330,
        nb_filles_force: 2,
      }),
      null,
    );
    expect(r.nb_poses_laize).toBe(2);
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
