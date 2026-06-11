import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConsommationStock } from "./ConsommationStock";

let fetchSpy: ReturnType<typeof vi.fn>;
let conso409 = false;

const PROPOSITION = {
  ml_requis: 1000,
  lignes: [
    {
      bobine_id: 10,
      emplacement: "A.0.25",
      laize_mm: 330,
      ml_restant: 1500,
      ml_propose: 1000,
    },
  ],
  stock_suffisant: true,
  manque_ml: 0,
};

function installFetchMock() {
  fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const ok = (body: unknown, status = 200) =>
      ({ ok: true, status, statusText: "OK", json: async () => body }) as Response;

    if (url.includes("/proposition-consommation")) return ok(PROPOSITION);
    if (url.includes("/consommer") && method === "POST") {
      if (conso409) {
        return {
          ok: false,
          status: 409,
          statusText: "Conflict",
          json: async () => ({ detail: "stock insuffisant" }),
        } as Response;
      }
      const body = JSON.parse((init?.body as string) ?? "{}");
      const ml = body.lignes.reduce(
        (s: number, l: { ml: number }) => s + l.ml,
        0,
      );
      return ok(
        {
          mouvements: [
            {
              id: 1,
              bobine_id: 10,
              type: "sortie",
              ml,
              date: "2026-06-11T10:00:00",
              motif: null,
              reference: null,
              devis_id: 5,
            },
          ],
          bobines: [],
        },
        201,
      );
    }
    if (url.includes("/annuler-consommation") && method === "POST") {
      return ok({ mouvements: [], bobines: [] }, 201);
    }
    throw new Error(`No mock for ${method} ${url}`);
  });
  global.fetch = fetchSpy as unknown as typeof fetch;
}

const calledConsommer = () =>
  fetchSpy.mock.calls.some(
    (c) =>
      /\/api\/devis\/5\/consommer$/.test(String(c[0])) &&
      (c[1] as RequestInit)?.method === "POST",
  );

describe("ConsommationStock — S3 consommer le stock", () => {
  beforeEach(() => {
    window.localStorage.clear();
    conso409 = false;
    installFetchMock();
  });
  afterEach(() => vi.restoreAllMocks());

  it("affiche la proposition FIFO (besoin + lignes ajustables)", async () => {
    render(<ConsommationStock devisId={5} />);
    await screen.findByTestId("consommation-stock");
    expect(screen.getByTestId("conso-ligne-10")).toHaveTextContent("A.0.25");
    expect(screen.getByTestId("consommation-stock")).toHaveTextContent(
      /1\s?000 ml/,
    );
    // Stock suffisant + ml proposé = requis → pas de bandeau manque.
    expect(screen.queryByTestId("manque-bandeau")).toBeNull();
  });

  it("ml sélectionné < requis → bandeau manque (non bloquant)", async () => {
    render(<ConsommationStock devisId={5} />);
    await screen.findByTestId("conso-ml-10");
    await userEvent.clear(screen.getByTestId("conso-ml-10"));
    await userEvent.type(screen.getByTestId("conso-ml-10"), "500");
    await waitFor(() =>
      expect(screen.getByTestId("manque-bandeau")).toBeInTheDocument(),
    );
  });

  it("consommer → POST → vue « consommé » + Annuler", async () => {
    render(<ConsommationStock devisId={5} />);
    await screen.findByTestId("consommer");
    await userEvent.click(screen.getByTestId("consommer"));
    await waitFor(() => expect(calledConsommer()).toBe(true));
    await screen.findByTestId("consomme-view");
    expect(screen.getByTestId("annuler-consommation")).toBeInTheDocument();
  });

  it("409 stock insuffisant → géré (pas de crash, reste en proposition)", async () => {
    conso409 = true;
    render(<ConsommationStock devisId={5} />);
    await screen.findByTestId("consommer");
    await userEvent.click(screen.getByTestId("consommer"));
    await waitFor(() => expect(calledConsommer()).toBe(true));
    // Pas de vue consommée, le bloc reste affiché.
    expect(screen.queryByTestId("consomme-view")).toBeNull();
    expect(screen.getByTestId("consommer")).toBeInTheDocument();
  });
});
