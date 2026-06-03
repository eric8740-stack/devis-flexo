import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DevisListResponse } from "@/lib/api";

// Verrou du reroute "Nouveau devis" -> flux optimisation : les 2 CTA de
// création de la page /devis pointent vers /optimisation (et non plus
// /devis/nouveau, conservé en legacy accessible par URL directe).

const listDevisMock = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listDevis: (...args: Parameters<typeof actual.listDevis>) =>
      listDevisMock(...args),
  };
});

import DevisListPage from "./page";

function emptyResponse(): DevisListResponse {
  return {
    items: [],
    total: 0,
    page: 1,
    per_page: 25,
  } as DevisListResponse;
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("DevisListPage — CTA création vers /optimisation", () => {
  it("le bouton d'en-tête '+ Nouveau devis' pointe vers /optimisation", async () => {
    listDevisMock.mockResolvedValue(emptyResponse());
    render(<DevisListPage />);

    const lien = await screen.findByRole("link", { name: "+ Nouveau devis" });
    expect(lien).toHaveAttribute("href", "/optimisation");
  });

  it("le CTA état vide 'Créer un devis' pointe vers /optimisation", async () => {
    listDevisMock.mockResolvedValue(emptyResponse());
    render(<DevisListPage />);

    // L'état vide s'affiche une fois la liste (vide) chargée.
    await waitFor(() =>
      expect(
        screen.getByText("Aucun devis pour le moment."),
      ).toBeInTheDocument(),
    );
    const lien = screen.getByRole("link", { name: "Créer un devis" });
    expect(lien).toHaveAttribute("href", "/optimisation");
  });
});
