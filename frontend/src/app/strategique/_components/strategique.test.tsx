import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";

import { CoutsSection } from "./CoutsSection";
import { RoulageSection } from "./RoulageSection";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual, // conserve MODES_ROULAGE et les types
    getConfigCouts: vi.fn(),
    updateConfigCouts: vi.fn(),
    listConfigRoulage: vi.fn(),
    createConfigRoulage: vi.fn(),
    updateConfigRoulage: vi.fn(),
    deleteConfigRoulage: vi.fn(),
  };
});

const COUTS = {
  id: 1,
  cout_exploitation_machine_eur_h: 50,
  cout_operateur_eur_h: 25,
  cout_energies_eur_h: 3.5,
  cout_fixe_atelier_eur_mois: 2500,
  cout_fixe_maintenance_eur_mois: 800,
  marge_standard_pct: 35,
  buffer_rebut_pct: 2.5,
  buffer_setup_pct: 1,
  // Phase 2 Lot 4a — coûts migrés depuis TarifPoste (édités dans
  // ConfigCoutsChamps, cf. ConfigCoutsChamps.test.tsx).
  marge_confort_roulage_mm: 5,
  cliche_prix_couleur_eur: 45,
  outil_base_eur: 300,
  outil_par_trace_eur: 0.8,
  surcout_forme_speciale_facteur: 1.3,
  calage_forfait_eur: 120,
  finitions_prix_m2_eur: 0.35,
  date_creation: "2026-05-27T00:00:00Z",
  date_maj: "2026-05-27T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CoutsSection", () => {
  it("charge la config et enregistre la marge modifiée", async () => {
    vi.mocked(api.getConfigCouts).mockResolvedValue(COUTS);
    vi.mocked(api.updateConfigCouts).mockResolvedValue({
      ...COUTS,
      marge_standard_pct: 42,
    });

    render(<CoutsSection />);

    // Valeur template chargée.
    const margeInput = await screen.findByLabelText(/Marge standard/);
    expect((margeInput as HTMLInputElement).value).toBe("35");

    fireEvent.change(margeInput, { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    await waitFor(() => {
      expect(api.updateConfigCouts).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(api.updateConfigCouts).mock.calls[0][0]).toMatchObject({
      marge_standard_pct: 42,
      cout_operateur_eur_h: 25, // PUT envoie tous les champs
    });
  });
});

describe("RoulageSection", () => {
  it("liste les formats et crée un nouveau format", async () => {
    vi.mocked(api.listConfigRoulage).mockResolvedValue([
      {
        id: 7,
        format_libelle: "A5",
        mode_roulage: "helicoidal",
        debit_mm_s: 280,
        rebut_pct: 3,
        date_creation: "2026-05-27T00:00:00Z",
        date_maj: "2026-05-27T00:00:00Z",
      },
    ]);
    vi.mocked(api.createConfigRoulage).mockResolvedValue({
      id: 8,
      format_libelle: "A4",
      mode_roulage: "alterne",
      debit_mm_s: 250,
      rebut_pct: 3,
      date_creation: "2026-05-27T00:00:00Z",
      date_maj: "2026-05-27T00:00:00Z",
    });

    render(<RoulageSection />);

    // Le format seedé A5 est listé.
    await waitFor(() => {
      expect(
        (screen.getByLabelText("Format") as HTMLInputElement).value
      ).toBe("A5");
    });

    // Ajout d'un format via le formulaire.
    fireEvent.change(screen.getByLabelText("Nouveau format"), {
      target: { value: "A4" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Ajouter/ }));

    await waitFor(() => {
      expect(api.createConfigRoulage).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(api.createConfigRoulage).mock.calls[0][0]).toMatchObject({
      format_libelle: "A4",
    });
  });

  it("refuse l'ajout d'un format vide (pas d'appel API)", async () => {
    vi.mocked(api.listConfigRoulage).mockResolvedValue([]);
    render(<RoulageSection />);
    await waitFor(() => expect(api.listConfigRoulage).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Ajouter/ }));
    expect(api.createConfigRoulage).not.toHaveBeenCalled();
  });
});
