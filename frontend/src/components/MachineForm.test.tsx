import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MachineForm } from "./MachineForm";

// B2 — vitest du bloc « Paramètres optimisation » de MachineForm.
// Mocke listMachineModulesDisponibles (endpoint backend /api/machines/
// modules-disponibles) pour controler la liste rendue.

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listMachineModulesDisponibles: vi.fn(),
  };
});

const { listMachineModulesDisponibles } = await import("@/lib/api");

function setupModules(modules: string[]) {
  vi.mocked(listMachineModulesDisponibles).mockResolvedValue(modules);
}

describe("MachineForm — bloc Paramètres optimisation (B2)", () => {
  it("rend les 3 champs optim distincts des champs cost_engine", async () => {
    setupModules(["hot_stamping", "retournement_laize"]);
    render(<MachineForm onSubmit={vi.fn()} />);

    // Le titre du bloc DISTINCT est present.
    expect(
      screen.getByRole("heading", { name: /paramètres optimisation/i }),
    ).toBeInTheDocument();

    // Les 3 champs B2 sont presents (pas de vitesse_pratique - depreciee).
    expect(screen.getByLabelText(/laize utile \(mm\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/nb postes découpe/i)).toBeInTheDocument();

    // Le multi-select options se peuple apres le fetch.
    await waitFor(() => {
      expect(screen.getByLabelText("hot_stamping")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("retournement_laize")).toBeInTheDocument();
  });

  it("ne montre PAS d'input vitesse_pratique_m_min (B2 : une seule vitesse réelle)", () => {
    setupModules([]);
    render(<MachineForm onSubmit={vi.fn()} />);
    expect(
      screen.queryByLabelText(/vitesse pratique/i),
    ).not.toBeInTheDocument();
  });

  it("affiche le bon label « Vitesse réelle de production » + aide chiffrage+optim", () => {
    setupModules([]);
    render(<MachineForm onSubmit={vi.fn()} />);
    expect(
      screen.getByLabelText(/vitesse réelle de production/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/pilote le chiffrage et l.optimisation/i),
    ).toBeInTheDocument();
  });

  it("persiste les 3 champs optim au submit (laize_utile, nb_postes, options)", async () => {
    setupModules(["hot_stamping", "lamination", "retournement_laize"]);
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<MachineForm onSubmit={onSubmit} />);

    // Champs cost_engine obligatoires (sinon submit invalide).
    await user.type(screen.getByLabelText(/nom \*/i), "MA Test B2");
    fireEvent.change(screen.getByLabelText(/laize max \(mm\)/i), {
      target: { value: "330" },
    });
    fireEvent.change(screen.getByLabelText(/vitesse réelle de production/i), {
      target: { value: "100" },
    });
    fireEvent.change(screen.getByLabelText(/durée calage \(h\)/i), {
      target: { value: "1" },
    });

    // Champs optim B2 (vrai test du bloc nouveau).
    fireEvent.change(screen.getByLabelText(/laize utile \(mm\)/i), {
      target: { value: "320" },
    });
    fireEvent.change(screen.getByLabelText(/nb postes découpe/i), {
      target: { value: "2" },
    });
    // Coche 2 modules sur 3.
    await waitFor(() => {
      expect(screen.getByLabelText("hot_stamping")).toBeInTheDocument();
    });
    await user.click(screen.getByLabelText("hot_stamping"));
    await user.click(screen.getByLabelText("lamination"));

    // fireEvent.submit bypasse la validation HTML5 (qui peut bloquer
    // les inputs number a cause de min/max sur les fireEvent.change ci-dessus).
    const form = screen
      .getByRole("button", { name: /enregistrer/i })
      .closest("form")!;
    fireEvent.submit(form);

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0][0];
    expect(payload.laize_utile_mm).toBe(320);
    expect(payload.nb_postes_decoupe).toBe(2);
    expect(payload.options).toEqual(["hot_stamping", "lamination"]);
    // Le champ cost_engine SACRE est intact.
    expect(payload.vitesse_moyenne_m_h).toBe(100 * 60);
    // B2 : pas de vitesse_pratique_m_min dans le payload.
    expect("vitesse_pratique_m_min" in payload).toBe(false);
  });

  it("affiche un message d'aide si aucun module n'est seedé", async () => {
    setupModules([]);
    render(<MachineForm onSubmit={vi.fn()} />);

    await waitFor(() => {
      expect(
        screen.getByText(/aucun module.*option-fabrication seedé/i),
      ).toBeInTheDocument();
    });
  });
});
