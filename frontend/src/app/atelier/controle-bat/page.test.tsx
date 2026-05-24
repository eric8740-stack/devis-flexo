import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/types/auth";

// Sprint 15 Lot A — tests RTL de l'écran atelier Contrôle BAT.
// Couvre gate has_flexocheck, état vide, rendu cards, état erreur.

// Mock useAuth : permet de stuber `user` dans chaque test.
const useAuthMock = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

import AtelierControleBatPage from "./page";

function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: "ops@acme.test",
    nom_contact: "Op Atelier",
    entreprise_id: 1,
    nom_entreprise: "ACME",
    is_admin: false,
    is_active: true,
    date_creation: "2026-01-01T00:00:00",
    date_derniere_connexion: null,
    has_flexocheck: true,
    ...overrides,
  };
}

interface MockResponse {
  urlPart: string;
  body: unknown;
  status?: number;
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
    const status = match.status ?? 200;
    return {
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? "OK" : "Error",
      json: async () => match.body,
    } as Response;
  }) as typeof fetch;
}

describe("AtelierControleBatPage — Lot A", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useAuthMock.mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("user sans has_flexocheck : message d'accès, pas d'appel API", async () => {
    useAuthMock.mockReturnValue({
      user: buildUser({ has_flexocheck: false }),
    });
    const fetchSpy = vi.fn();
    global.fetch = fetchSpy as unknown as typeof fetch;

    render(<AtelierControleBatPage />);

    expect(
      screen.getByText(/Module FlexoCheck non activé/i),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("user sans user du tout (non chargé) : message d'accès, pas d'appel API", () => {
    useAuthMock.mockReturnValue({ user: null });
    const fetchSpy = vi.fn();
    global.fetch = fetchSpy as unknown as typeof fetch;

    render(<AtelierControleBatPage />);

    expect(
      screen.getByText(/Module FlexoCheck non activé/i),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("user FlexoCheck + liste vide : EmptyState affiché", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    installFetchMock([
      {
        urlPart: "/api/flexocheck/productions-actives",
        body: { items: [], total: 0 },
      },
    ]);

    render(<AtelierControleBatPage />);

    await waitFor(() =>
      expect(
        screen.getByText(/Aucune production en cours/i),
      ).toBeInTheDocument(),
    );
  });

  it("user FlexoCheck + N productions : N cards rendues avec lien contrôle", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    installFetchMock([
      {
        urlPart: "/api/flexocheck/productions-actives",
        body: {
          items: [
            {
              devis_id: 1,
              client: "ACME",
              designation: "DEV-2026-0001",
              machine: "MA P5",
              bat_reference_uploaded: true,
            },
            {
              devis_id: 2,
              client: null,
              designation: "DEV-2026-0002",
              machine: "MA P7",
              bat_reference_uploaded: false,
            },
          ],
          total: 2,
        },
      },
    ]);

    render(<AtelierControleBatPage />);

    await waitFor(() =>
      expect(screen.getByTestId("production-1")).toBeInTheDocument(),
    );

    const card1 = screen.getByTestId("production-1");
    expect(card1).toHaveTextContent("DEV-2026-0001");
    expect(card1).toHaveTextContent("ACME");
    expect(card1).toHaveTextContent("MA P5");
    // BAT présent → badge "BAT rattaché", bouton "Remplacer le BAT" actif,
    // lien "Ouvrir le contrôle" rendu vers la route détail (Lot C).
    expect(card1).toHaveTextContent(/BAT rattaché/i);
    expect(card1).toHaveTextContent(/Remplacer le BAT/i);
    const link1 = card1.querySelector("a[href='/atelier/controle-bat/1']");
    expect(link1).not.toBeNull();

    const card2 = screen.getByTestId("production-2");
    expect(card2).toHaveTextContent("DEV-2026-0002");
    // BAT absent → badge "BAT manquant", bouton "Rattacher le BAT", pas de
    // lien vers le contrôle (Lot C exige bat_reference_uploaded).
    expect(card2).toHaveTextContent(/BAT manquant/i);
    expect(card2).toHaveTextContent(/Rattacher le BAT/i);
    const link2 = card2.querySelector("a[href='/atelier/controle-bat/2']");
    expect(link2).toBeNull();
  });

  it("clic sur 'Rattacher le BAT' : ouvre le dialog d'upload pour le bon devis", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    installFetchMock([
      {
        urlPart: "/api/flexocheck/productions-actives",
        body: {
          items: [
            {
              devis_id: 7,
              client: "BetaCorp",
              designation: "DEV-2026-0007",
              machine: "MA P9",
              bat_reference_uploaded: false,
            },
          ],
          total: 1,
        },
      },
    ]);

    render(<AtelierControleBatPage />);
    const card = await screen.findByTestId("production-7");
    await userEvent.click(
      within(card).getByRole("button", { name: /Rattacher le BAT/i }),
    );

    // Dialog ouvert : le titre contient le numéro du devis ciblé. Radix
    // Dialog rend via portal sur document.body, donc on cherche au niveau
    // global plutôt que scoped à la card.
    await waitFor(() =>
      expect(
        screen.getByText(/Rattacher le BAT — DEV-2026-0007/),
      ).toBeInTheDocument(),
    );
  });

  it("erreur API (500) : bandeau alert affiché, pas de cards", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    installFetchMock([
      {
        urlPart: "/api/flexocheck/productions-actives",
        status: 500,
        body: { detail: "Boom" },
      },
    ]);

    render(<AtelierControleBatPage />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument(),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/Boom/);
    expect(screen.queryByLabelText("Productions actives")).toBeNull();
  });
});
