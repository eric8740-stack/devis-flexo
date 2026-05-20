// Format vitest/jest standard. Aucun runner n'est installé côté frontend
// au moment de l'écriture (Sprint 14) — ces tests sont prêts à tourner
// dès qu'on ajoute `npm i -D vitest` (ou jest).

import { describe, it, expect } from "vitest";

import { conseilsAdhesif } from "./adhesif-helper";

const STANDARD = "Adhésif permanent standard";

describe("conseilsAdhesif — fallback standard", () => {
  it("retourne le conseil standard si conditions null", () => {
    expect(conseilsAdhesif(null)).toEqual([STANDARD]);
  });

  it("retourne le conseil standard si conditions undefined", () => {
    expect(conseilsAdhesif(undefined)).toEqual([STANDARD]);
  });

  it("retourne le conseil standard si aucun critère ne s'applique", () => {
    expect(
      conseilsAdhesif({
        humidite_pct: 50,
        t_min_c: 5,
        t_max_c: 30,
        lieu: "interieur",
      })
    ).toEqual([STANDARD]);
  });

  it("retourne le conseil standard sur objet vide", () => {
    expect(conseilsAdhesif({})).toEqual([STANDARD]);
  });
});

describe("conseilsAdhesif — règles individuelles", () => {
  it("humidité > 70 → conseil tropical", () => {
    const r = conseilsAdhesif({ humidite_pct: 75 });
    expect(r).toContain("Privilégier adhésif tropical (résistance humidité)");
    expect(r).not.toContain(STANDARD);
  });

  it("t_min < 0 → conseil froid négatif", () => {
    const r = conseilsAdhesif({ t_min_c: -5 });
    expect(r).toContain("Adhésif froid négatif requis");
  });

  it("t_max > 60 → conseil haute température", () => {
    const r = conseilsAdhesif({ t_max_c: 80 });
    expect(r).toContain("Adhésif haute température (cuisson, four)");
  });

  it("lieu === 'exterieur' → conseil UV-résistant", () => {
    const r = conseilsAdhesif({ lieu: "exterieur" });
    expect(r).toContain("Adhésif UV-résistant");
  });
});

describe("conseilsAdhesif — seuils stricts (bord)", () => {
  it("humidité = 70 ne déclenche PAS le tropical (> strict)", () => {
    expect(conseilsAdhesif({ humidite_pct: 70 })).toEqual([STANDARD]);
  });

  it("t_min = 0 ne déclenche PAS le froid négatif (< strict)", () => {
    expect(conseilsAdhesif({ t_min_c: 0 })).toEqual([STANDARD]);
  });

  it("t_max = 60 ne déclenche PAS la haute température (> strict)", () => {
    expect(conseilsAdhesif({ t_max_c: 60 })).toEqual([STANDARD]);
  });
});

describe("conseilsAdhesif — cumul de conseils", () => {
  it("humidité > 70 + lieu exterieur → 2 conseils", () => {
    const r = conseilsAdhesif({ humidite_pct: 90, lieu: "exterieur" });
    expect(r).toHaveLength(2);
    expect(r).toContain("Privilégier adhésif tropical (résistance humidité)");
    expect(r).toContain("Adhésif UV-résistant");
  });

  it("4 critères déclenchés → 4 conseils, pas de standard", () => {
    const r = conseilsAdhesif({
      humidite_pct: 80,
      t_min_c: -10,
      t_max_c: 100,
      lieu: "exterieur",
    });
    expect(r).toHaveLength(4);
    expect(r).not.toContain(STANDARD);
  });
});

describe("conseilsAdhesif — robustesse types", () => {
  it("humidité null ignorée", () => {
    expect(conseilsAdhesif({ humidite_pct: null, lieu: "exterieur" })).toEqual([
      "Adhésif UV-résistant",
    ]);
  });

  it("lieu 'interieur' ne déclenche pas UV-résistant", () => {
    expect(conseilsAdhesif({ lieu: "interieur" })).toEqual([STANDARD]);
  });

  it("lieu inconnu (string libre) ne déclenche pas UV-résistant", () => {
    expect(conseilsAdhesif({ lieu: "entrepot-froid" })).toEqual([STANDARD]);
  });
});
