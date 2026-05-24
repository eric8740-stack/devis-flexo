import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DialogValiderProduction } from "./DialogValiderProduction";

// Sprint 15 Lot E — tests RTL du dialog de validation finale.
// Mocke decideControleBat depuis le client API.

const decideMock = vi.fn();
vi.mock("@/lib/api/controleBat", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/api/controleBat")>();
  return {
    ...actual,
    decideControleBat: (
      ...args: Parameters<typeof actual.decideControleBat>
    ) => decideMock(...args),
  };
});

function renderDialog(
  overrides: Partial<{
    open: boolean;
    onOpenChange: (b: boolean) => void;
    onValidated: (res: unknown) => void;
  }> = {},
) {
  const onOpenChange = overrides.onOpenChange ?? vi.fn();
  const onValidated = overrides.onValidated ?? vi.fn();
  const open = overrides.open ?? true;
  render(
    <DialogValiderProduction
      controleId={101}
      devisNumero="DEV-2026-0042"
      open={open}
      onOpenChange={onOpenChange}
      onValidated={onValidated}
    />,
  );
  return { onOpenChange, onValidated };
}

describe("DialogValiderProduction — Lot E", () => {
  beforeEach(() => {
    decideMock.mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("titre + champs visibles, numéro devis dans le titre", () => {
    renderDialog();
    expect(
      screen.getByText(/Valider la production — DEV-2026-0042/),
    ).toBeInTheDocument();
    expect(screen.getByTestId("decideur-input")).toBeInTheDocument();
    expect(screen.getByTestId("motif-input")).toBeInTheDocument();
  });

  it("submit sans décideur : erreur 'obligatoire', pas d'appel API", async () => {
    renderDialog();
    await userEvent.click(
      screen.getByRole("button", { name: /✅ Valider la production/i }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/obligatoire/i);
    expect(decideMock).not.toHaveBeenCalled();
  });

  it("submit avec décideur + motif : appel decideControleBat, callbacks, fermeture", async () => {
    decideMock.mockResolvedValueOnce({
      controle_id: 101,
      devis_id: 7,
      decision_finale: "valider",
      decideur: "J. Martin",
      motif: "Écart mineur accepté",
      decided_at: "2026-05-24T11:00:00",
    });

    const { onOpenChange, onValidated } = renderDialog();
    await userEvent.type(
      screen.getByTestId("decideur-input"),
      "J. Martin",
    );
    await userEvent.type(
      screen.getByTestId("motif-input"),
      "Écart mineur accepté",
    );
    await userEvent.click(
      screen.getByRole("button", { name: /✅ Valider la production/i }),
    );

    await waitFor(() => expect(decideMock).toHaveBeenCalledTimes(1));
    expect(decideMock).toHaveBeenCalledWith(101, {
      decision_finale: "valider",
      decideur: "J. Martin",
      motif: "Écart mineur accepté",
    });
    expect(onValidated).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("motif vide : envoyé sans motif (undefined)", async () => {
    decideMock.mockResolvedValueOnce({
      controle_id: 101,
      devis_id: 7,
      decision_finale: "valider",
      decideur: "J. M",
      motif: null,
      decided_at: "2026-05-24T11:00:00",
    });

    renderDialog();
    await userEvent.type(screen.getByTestId("decideur-input"), "J. M");
    await userEvent.click(
      screen.getByRole("button", { name: /✅ Valider la production/i }),
    );

    await waitFor(() => expect(decideMock).toHaveBeenCalledTimes(1));
    expect(decideMock).toHaveBeenCalledWith(101, {
      decision_finale: "valider",
      decideur: "J. M",
      motif: undefined,
    });
  });

  it("erreur API : alerte affichée, dialog reste ouvert, pas de onValidated", async () => {
    decideMock.mockRejectedValueOnce(
      new Error("POST → 409 Décision déjà enregistrée"),
    );

    const { onOpenChange, onValidated } = renderDialog();
    await userEvent.type(screen.getByTestId("decideur-input"), "J. M");
    await userEvent.click(
      screen.getByRole("button", { name: /✅ Valider la production/i }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Décision déjà enregistrée/);
    expect(onValidated).not.toHaveBeenCalled();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
