import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CylindresOnglet } from "./CylindresOnglet";

// Non-régression du fix `fix(ui): mon-parc cylindres désactivés visibles
// + filtre Toutes porte-clichés`. Vérifie qu'un cylindre `actif=false`
// s'affiche désormais en permanence avec un badge "Désactivé", sans
// avoir à cocher une option dédiée. Le helper `listCylindres(null)`
// fait deux fetch parallèles vers /api/cylindres?actif=true|false et
// concat — on mocke les deux réponses.

interface MockResponse {
  urlPart: string;
  body: unknown;
}

function installFetchMock(responses: MockResponse[]) {
  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : (input as Request).url;
    const match = responses.find((r) => url.includes(r.urlPart));
    if (!match) {
      throw new Error(`No mock for ${url}`);
    }
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => match.body,
    } as Response;
  }) as typeof fetch;
}

describe("CylindresOnglet — fix cylindres désactivés visibles", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("affiche les cylindres actifs ET désactivés, badge 'Désactivé' sur les inactifs", async () => {
    installFetchMock([
      {
        // 1er fetch parallèle : actifs.
        urlPart: "/api/cylindres?actif=true",
        body: [
          {
            id: 1,
            nb_dents: 104,
            developpe_mm: "330.20",
            actif: true,
            notes: null,
            date_creation: "2026-05-01T00:00:00",
          },
        ],
      },
      {
        // 2e fetch parallèle : désactivés.
        urlPart: "/api/cylindres?actif=false",
        body: [
          {
            id: 2,
            nb_dents: 96,
            developpe_mm: "304.80",
            actif: false,
            notes: "Cylindre HS",
            date_creation: "2026-04-01T00:00:00",
          },
        ],
      },
    ]);

    render(<CylindresOnglet />);

    // Les deux cylindres doivent être rendus une fois les fetch résolus.
    await waitFor(() =>
      expect(screen.getByText("104 dents")).toBeInTheDocument(),
    );
    expect(screen.getByText("96 dents")).toBeInTheDocument();

    // Le cylindre actif=false porte le badge "Désactivé", l'actif non.
    const cardActif = screen.getByText("104 dents").closest("div.group");
    const cardInactif = screen.getByText("96 dents").closest("div.group");
    expect(cardActif).not.toBeNull();
    expect(cardInactif).not.toBeNull();
    expect(
      within(cardInactif as HTMLElement).getByText("Désactivé"),
    ).toBeInTheDocument();
    expect(
      within(cardActif as HTMLElement).queryByText("Désactivé"),
    ).toBeNull();
  });
});
