import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";

import {
  CalageCoutsSection,
  FinitionsCoutsSection,
  MargeRoulageSection,
  OutilsCoutsSection,
} from "./ConfigCoutsChamps";

// Lot 4b — édition des 7 coûts ConfigCouts (ex-TarifPoste, cf. Lot 4a).
// On mocke useToast pour vérifier le retour utilisateur (succès/erreur).
const { toastMock } = vi.hoisted(() => ({ toastMock: vi.fn() }));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: toastMock }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getConfigCouts: vi.fn(),
    updateConfigCouts: vi.fn(),
  };
});

const COUTS: api.ConfigCouts = {
  id: 1,
  cout_exploitation_machine_eur_h: 50,
  cout_operateur_eur_h: 25,
  cout_energies_eur_h: 3.5,
  cout_fixe_atelier_eur_mois: 2500,
  cout_fixe_maintenance_eur_mois: 800,
  marge_standard_pct: 35,
  buffer_rebut_pct: 2.5,
  buffer_setup_pct: 1,
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
  vi.mocked(api.getConfigCouts).mockResolvedValue(COUTS);
});

describe("OutilsCoutsSection", () => {
  it("affiche les 4 coûts outils depuis le GET", async () => {
    render(<OutilsCoutsSection />);

    const cliche = await screen.findByLabelText(/Cliché/);
    expect((cliche as HTMLInputElement).value).toBe("45");
    expect(
      (screen.getByLabelText(/Outil de découpe \(base\)/) as HTMLInputElement)
        .value
    ).toBe("300");
    expect(
      (screen.getByLabelText(/€\/tracé/) as HTMLInputElement).value
    ).toBe("0.8");
    expect(
      (screen.getByLabelText(/Surcoût forme spéciale/) as HTMLInputElement)
        .value
    ).toBe("1.3");
  });

  it("PUT partiel : n'envoie QUE les champs modifiés", async () => {
    vi.mocked(api.updateConfigCouts).mockResolvedValue({
      ...COUTS,
      outil_base_eur: 350,
    });

    render(<OutilsCoutsSection />);

    const outilBase = await screen.findByLabelText(/Outil de découpe \(base\)/);
    fireEvent.change(outilBase, { target: { value: "350" } });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    await waitFor(() => {
      expect(api.updateConfigCouts).toHaveBeenCalledTimes(1);
    });
    // Strict : uniquement le champ modifié, pas les 3 autres ni le reste
    // de ConfigCouts.
    expect(vi.mocked(api.updateConfigCouts).mock.calls[0][0]).toEqual({
      outil_base_eur: 350,
    });
  });

  it("sans modification : aucun appel API", async () => {
    render(<OutilsCoutsSection />);
    await screen.findByLabelText(/Cliché/);

    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));
    expect(api.updateConfigCouts).not.toHaveBeenCalled();
    expect(toastMock).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Aucune modification à enregistrer" })
    );
  });

  it("affiche l'erreur API à l'enregistrement", async () => {
    vi.mocked(api.updateConfigCouts).mockRejectedValue(
      new Error("500 Internal Server Error")
    );

    render(<OutilsCoutsSection />);

    const cliche = await screen.findByLabelText(/Cliché/);
    fireEvent.change(cliche, { target: { value: "60" } });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Échec de l'enregistrement",
          variant: "destructive",
          description: expect.stringContaining("500"),
        })
      );
    });
  });

  it("affiche l'erreur API au chargement", async () => {
    vi.mocked(api.getConfigCouts).mockRejectedValue(new Error("réseau HS"));

    render(<OutilsCoutsSection />);

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Erreur de chargement",
          variant: "destructive",
        })
      );
    });
  });
});

describe("CalageCoutsSection", () => {
  it("charge puis enregistre le forfait calage seul", async () => {
    vi.mocked(api.updateConfigCouts).mockResolvedValue({
      ...COUTS,
      calage_forfait_eur: 150,
    });

    render(<CalageCoutsSection />);

    const forfait = await screen.findByLabelText(/Forfait calage/);
    expect((forfait as HTMLInputElement).value).toBe("120");

    fireEvent.change(forfait, { target: { value: "150" } });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    await waitFor(() => {
      expect(api.updateConfigCouts).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(api.updateConfigCouts).mock.calls[0][0]).toEqual({
      calage_forfait_eur: 150,
    });
  });
});

describe("FinitionsCoutsSection", () => {
  it("affiche le prix finitions depuis le GET", async () => {
    render(<FinitionsCoutsSection />);

    const finitions = await screen.findByLabelText(/Finitions/);
    expect((finitions as HTMLInputElement).value).toBe("0.35");
  });
});

describe("MargeRoulageSection", () => {
  it("charge puis enregistre la marge de confort seule", async () => {
    vi.mocked(api.updateConfigCouts).mockResolvedValue({
      ...COUTS,
      marge_confort_roulage_mm: 8,
    });

    render(<MargeRoulageSection />);

    const marge = await screen.findByLabelText(/Marge de confort/);
    expect((marge as HTMLInputElement).value).toBe("5");

    fireEvent.change(marge, { target: { value: "8" } });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/ }));

    await waitFor(() => {
      expect(api.updateConfigCouts).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(api.updateConfigCouts).mock.calls[0][0]).toEqual({
      marge_confort_roulage_mm: 8,
    });
  });
});
