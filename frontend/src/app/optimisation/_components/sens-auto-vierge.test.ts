import { describe, expect, it } from "vitest";

import { sensAutoForTypeEntree } from "./sens-auto-vierge";

describe("sensAutoForTypeEntree", () => {
  describe("passage à 'vierge'", () => {
    it("remappe les sens face ext (SE1-SE4) vers SE0", () => {
      for (const s of ["SE1", "SE2", "SE3", "SE4"] as const) {
        expect(sensAutoForTypeEntree(s, "vierge")).toBe("SE0");
      }
    });

    it("remappe les sens face int (SE5-SE8) vers SE9", () => {
      for (const s of ["SE5", "SE6", "SE7", "SE8"] as const) {
        expect(sensAutoForTypeEntree(s, "vierge")).toBe("SE9");
      }
    });

    it("laisse SE0 / SE9 inchangés (déjà sur sens vierge)", () => {
      expect(sensAutoForTypeEntree("SE0", "vierge")).toBe("SE0");
      expect(sensAutoForTypeEntree("SE9", "vierge")).toBe("SE9");
    });
  });

  describe("sortie de 'vierge'", () => {
    it("remappe SE0 vers SE1 (default ext imprimable) — type bat_pro_fourni", () => {
      expect(sensAutoForTypeEntree("SE0", "bat_pro_fourni")).toBe("SE1");
    });

    it("remappe SE9 vers SE5 (default int imprimable) — type a_designer", () => {
      expect(sensAutoForTypeEntree("SE9", "a_designer")).toBe("SE5");
    });

    it("laisse les autres sens (SE1-SE8) inchangés", () => {
      for (const s of [
        "SE1",
        "SE2",
        "SE3",
        "SE4",
        "SE5",
        "SE6",
        "SE7",
        "SE8",
      ] as const) {
        expect(sensAutoForTypeEntree(s, "bat_pro_fourni")).toBe(s);
        expect(sensAutoForTypeEntree(s, "a_designer")).toBe(s);
      }
    });
  });
});
