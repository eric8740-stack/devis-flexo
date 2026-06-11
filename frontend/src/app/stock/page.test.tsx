import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import StockPage from "./page";

let fetchSpy: ReturnType<typeof vi.fn>;

const BOBINE = {
  id: 10,
  matiere_id: 1,
  laize_mm: 330,
  epaisseur_microns: 50,
  ml_initial: 2000,
  ml_restant: 1500,
  rangee: "A",
  etage: 0,
  position: 25,
  statut: "en_stock",
  date_reception: null,
  fournisseur: null,
  reference_lot: null,
  emplacement: "A.0.25",
};

function installFetchMock() {
  fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const ok = (body: unknown, status = 200) =>
      ({ ok: true, status, statusText: "OK", json: async () => body }) as Response;

    if (url.includes("/api/matieres")) {
      return ok([{ id: 1, libelle: "PET", epaisseur_microns: 50 }]);
    }
    if (url.includes("/api/bobines") && method === "POST") {
      return ok({ ...BOBINE, id: 11 }, 201);
    }
    if (/\/api\/bobines\/\d+$/.test(url) && method === "DELETE") {
      return { ok: true, status: 204, statusText: "No Content" } as Response;
    }
    if (url.includes("/api/bobines") && method === "GET") {
      // Filtre statut=consommee → liste vide (pour le test de filtre).
      if (url.includes("statut=consommee")) return ok([]);
      return ok([BOBINE]);
    }
    throw new Error(`No mock for ${method} ${url}`);
  });
  global.fetch = fetchSpy as unknown as typeof fetch;
}

function calledWith(predicate: (url: string, init?: RequestInit) => boolean) {
  return fetchSpy.mock.calls.some((c) =>
    predicate(String(c[0]), c[1] as RequestInit),
  );
}

describe("StockPage — inventaire bobines", () => {
  beforeEach(() => {
    window.localStorage.clear();
    installFetchMock();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("liste les bobines (matière, emplacement, ml restant, statut)", async () => {
    render(<StockPage />);
    const row = await screen.findByTestId("stock-row-10");
    expect(row).toHaveTextContent("PET");
    expect(row).toHaveTextContent("A.0.25");
    expect(row).toHaveTextContent(/1\s?500 ml/);
    expect(row).toHaveTextContent("En stock");
  });

  it("filtre statut → recharge /api/bobines avec le paramètre", async () => {
    render(<StockPage />);
    await screen.findByTestId("stock-row-10");
    await userEvent.selectOptions(screen.getByTestId("filtre-statut"), "consommee");
    await waitFor(() =>
      expect(
        calledWith((u, i) => u.includes("/api/bobines?") && u.includes("statut=consommee") && (i?.method ?? "GET") === "GET"),
      ).toBe(true),
    );
    // Liste vide pour ce filtre → état vide affiché.
    await waitFor(() =>
      expect(screen.getByTestId("stock-vide")).toBeInTheDocument(),
    );
  });

  it("création : formulaire → POST /api/bobines", async () => {
    render(<StockPage />);
    await screen.findByTestId("stock-row-10");
    await userEvent.click(screen.getByTestId("stock-new"));
    await userEvent.selectOptions(screen.getByTestId("f-matiere"), "1");
    await userEvent.type(screen.getByTestId("f-laize"), "330");
    await userEvent.type(screen.getByTestId("f-rangee"), "A");
    await userEvent.type(screen.getByTestId("f-etage"), "0");
    await userEvent.type(screen.getByTestId("f-position"), "25");
    await userEvent.click(screen.getByTestId("f-submit"));
    await waitFor(() =>
      expect(
        calledWith(
          (u, i) =>
            u.endsWith("/api/bobines") && (i?.method ?? "") === "POST",
        ),
      ).toBe(true),
    );
  });

  it("suppression : confirmation puis DELETE /api/bobines/{id}", async () => {
    render(<StockPage />);
    await screen.findByTestId("stock-row-10");
    await userEvent.click(screen.getByTestId("del-10"));
    // Confirmation inline visible.
    await userEvent.click(screen.getByTestId("del-confirm-10"));
    await waitFor(() =>
      expect(
        calledWith(
          (u, i) =>
            /\/api\/bobines\/10$/.test(u) && (i?.method ?? "") === "DELETE",
        ),
      ).toBe(true),
    );
  });
});
