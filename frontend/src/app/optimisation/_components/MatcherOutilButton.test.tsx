import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Machine } from "@/lib/api";
import type { MatcherOutilMatch } from "@/lib/api/matcherOutil";

import { MatcherOutilButton } from "./MatcherOutilButton";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./OptimisationPoseStore";

// Sprint 14 Lot 4.5 — tests RTL du composant MatcherOutilButton.
// Couvre les 4 cas du brief : matches multiples (tri + propagation store),
// dropdown N machines (re-fetch), nouvel outil seul, 422 backend.

function buildFakeMachine(overrides: Partial<Machine> = {}): Machine {
  return {
    id: 1,
    nom: "Mark Andy P5",
    largeur_max_mm: 250,
    laize_max_mm: 250,
    vitesse_max_m_min: 100,
    vitesse_moyenne_m_h: 5000,
    duree_calage_h: 0.5,
    nb_couleurs: 8,
    cout_horaire_eur: 100,
    actif: true,
    commentaire: null,
    date_creation: "2026-01-01T00:00:00",
    date_maj: "2026-01-01T00:00:00",
    ...overrides,
  };
}

function buildFakeMatch(
  overrides: Partial<MatcherOutilMatch> = {},
): MatcherOutilMatch {
  return {
    cylindre_id: 10,
    nb_dents: 100,
    developpe_mm: "100.0",
    nb_poses_dev: 1,
    nb_poses_laize: 5,
    nb_poses_total: 5,
    cout_outil_eur: "120.00",
    score_efficacite: 0.95,
    ...overrides,
  };
}

interface MockResponse {
  urlPart: string;
  method?: string;
  body: unknown;
  status?: number;
}

function installFetchMock(responses: MockResponse[]) {
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : (input as Request).url;
    const method = init?.method ?? "GET";
    const match = responses.find((r) => {
      if (r.method && r.method !== method) return false;
      return url.includes(r.urlPart);
    });
    if (!match) {
      throw new Error(`No mock for ${method} ${url}`);
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

// Consumer minimal pour vérifier la propagation au store.
function StoreInspector() {
  const { outilSelectionne } = useOptimisationPose();
  return (
    <div data-testid="outil-selectionne">
      {outilSelectionne
        ? `cyl=${outilSelectionne.cylindre_id ?? "null"};dents=${outilSelectionne.nb_dents}`
        : "none"}
    </div>
  );
}

const DEFAULT_PROPS = {
  laizeEtiqMm: 100,
  devEtiqMm: 80,
  intervalleDevMm: 2,
  intervalleLaizeMm: 2,
};

function renderComponent(props = DEFAULT_PROPS) {
  return render(
    <OptimisationPoseProvider>
      <MatcherOutilButton {...props} />
      <StoreInspector />
    </OptimisationPoseProvider>,
  );
}

describe("MatcherOutilButton — Lot 4.5", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("happy path 1 machine + matches multiples : ordre conservé + clic propage store", async () => {
    installFetchMock([
      { urlPart: "/api/machines", body: [buildFakeMachine({ id: 1 })] },
      {
        urlPart: "/api/optimisation/matcher-outil",
        method: "POST",
        body: {
          matches: [
            buildFakeMatch({ cylindre_id: 10, nb_dents: 100, score_efficacite: 0.95 }),
            buildFakeMatch({ cylindre_id: 11, nb_dents: 96, score_efficacite: 0.85 }),
            buildFakeMatch({ cylindre_id: 12, nb_dents: 80, score_efficacite: 0.70 }),
          ],
          nb_matches: 3,
        },
      },
    ]);

    renderComponent();

    // Attendre fin du fetch machines → label info "Outils compatibles pour …"
    await waitFor(() =>
      expect(screen.getByText(/Outils compatibles pour/i)).toBeInTheDocument(),
    );
    // Pas de dropdown puisque 1 seule machine
    expect(screen.queryByLabelText("Machine")).toBeNull();

    await userEvent.click(
      screen.getByRole("button", { name: /Voir outils compatibles/i }),
    );

    await waitFor(() =>
      expect(screen.getByTestId("matcher-results")).toBeInTheDocument(),
    );
    const cards = screen.getAllByTestId(/^match-\d+$/);
    expect(cards).toHaveLength(3);
    expect(cards[0]).toHaveTextContent("Cylindre #10");
    expect(cards[1]).toHaveTextContent("Cylindre #11");
    expect(cards[2]).toHaveTextContent("Cylindre #12");

    // Clic sur le 2e match → propagation store
    await userEvent.click(cards[1]!);
    expect(screen.getByTestId("outil-selectionne")).toHaveTextContent(
      "cyl=11;dents=96",
    );
  });

  it("N machines : dropdown affiché + change selection reset matches", async () => {
    installFetchMock([
      {
        urlPart: "/api/machines",
        body: [
          buildFakeMachine({ id: 1, nom: "MA-1" }),
          buildFakeMachine({ id: 2, nom: "MA-2" }),
          buildFakeMachine({ id: 3, nom: "MA-3" }),
        ],
      },
      {
        urlPart: "/api/optimisation/matcher-outil",
        method: "POST",
        body: { matches: [buildFakeMatch()], nb_matches: 1 },
      },
    ]);

    renderComponent();

    await waitFor(() =>
      expect(screen.getByLabelText("Machine")).toBeInTheDocument(),
    );
    const select = screen.getByLabelText("Machine") as HTMLSelectElement;
    expect(select.options).toHaveLength(3);
    expect(select.value).toBe("1");

    // Lancer 1er match, voir résultats
    await userEvent.click(
      screen.getByRole("button", { name: /Voir outils compatibles/i }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("matcher-results")).toBeInTheDocument(),
    );

    // Changer de machine → les matches doivent disparaître
    await userEvent.selectOptions(select, "2");
    expect(select.value).toBe("2");
    expect(screen.queryByTestId("matcher-results")).toBeNull();
  });

  it("nouvel outil seul (cylindre_id=null) : carte spéciale rendue", async () => {
    installFetchMock([
      { urlPart: "/api/machines", body: [buildFakeMachine({ id: 1 })] },
      {
        urlPart: "/api/optimisation/matcher-outil",
        method: "POST",
        body: {
          matches: [
            buildFakeMatch({
              cylindre_id: null,
              nb_dents: 0,
              developpe_mm: "0",
              nb_poses_dev: 0,
              nb_poses_laize: 0,
              nb_poses_total: 0,
              cout_outil_eur: "200.00",
              score_efficacite: 0,
            }),
          ],
          nb_matches: 1,
        },
      },
    ]);

    renderComponent();
    await waitFor(() =>
      expect(screen.getByText(/Outils compatibles pour/i)).toBeInTheDocument(),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Voir outils compatibles/i }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("matcher-results")).toBeInTheDocument(),
    );

    expect(screen.getByText(/Nouvel outil à fabriquer/i)).toBeInTheDocument();
    // Affichage fr-FR : "200,00 €"
    expect(screen.getByText(/200,00 €/)).toBeInTheDocument();
  });

  it("422 backend : message d'erreur clair affiché en role=alert", async () => {
    installFetchMock([
      { urlPart: "/api/machines", body: [buildFakeMachine({ id: 1 })] },
      {
        urlPart: "/api/optimisation/matcher-outil",
        method: "POST",
        status: 422,
        body: { detail: "Étiquette trop grande pour le parc" },
      },
    ]);

    renderComponent();
    await waitFor(() =>
      expect(screen.getByText(/Outils compatibles pour/i)).toBeInTheDocument(),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Voir outils compatibles/i }),
    );

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument(),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      /trop grande ou aucun match faisable/i,
    );
    // Pas de cards rendues
    expect(screen.queryByTestId("matcher-results")).toBeNull();
  });
});
