import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  PlanBobinesSelectionIn,
  PlanificateurBobinesResponse,
} from "@/lib/api";

import { PlanificateurBobines } from "./PlanificateurBobines";

// Brief planificateur bobines (finition) — on vérifie :
//   1) inputs manquants → gate, pas de fetch
//   2) cas type → cartes rendues + badge recommandé
//   3) IMPOSE physiquement impossible → bandeau rouge + motif requis
//   4) « Choisir » → PUT /api/devis/{id}/plan-bobines (persistance)
//   5) Restauration initialSelection : la carte est marquée sélectionnée
//   6) Forçage IMPOSE : bouton désactivé sans motif ; envoie force_diametre
//      + motif_forcage avec motif

// Mock router (utilisé par le bouton « Appliquer cette quantité »).
const routerPushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPushMock }),
}));

let fetchSpy: ReturnType<typeof vi.fn>;

function installFetchMock(response: PlanificateurBobinesResponse) {
  fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : (input as Request).url;
    if (url.includes("/api/devis/planificateur-bobines")) {
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => response,
      } as Response;
    }
    if (url.match(/\/api\/devis\/\d+\/plan-bobines$/)) {
      // PUT persistance : on renvoie le body pour cohérence.
      const body = JSON.parse((init?.body as string) ?? "{}");
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => body,
      } as Response;
    }
    throw new Error(`No mock for ${url}`);
  });
  global.fetch = fetchSpy as unknown as typeof fetch;
}

function buildResponseSimple(): PlanificateurBobinesResponse {
  return {
    scenarios: [
      {
        cle: "A",
        titre: "Pleines + reliquat",
        repartition: [
          { nb_etiq_par_bobine: 2239, nb_bobines_par_piste: 1, diametre_mm: 200 },
          { nb_etiq_par_bobine: 1095, nb_bobines_par_piste: 1, diametre_mm: 150 },
        ],
        nb_bobines_par_piste: 2,
        nb_bobines_total: 6,
        quantite_totale_etiq: 10002,
        surprod_etiq: 2,
        q_ajustee: null,
        cout_total_eur: "45.50",
        cout_machine_eur: "20.00",
        cout_mandrins_eur: "25.50",
        mode_mandrins_optimal: "pre_coupe",
      },
      {
        cle: "B",
        titre: "Équilibrées",
        repartition: [
          { nb_etiq_par_bobine: 1667, nb_bobines_par_piste: 2, diametre_mm: 180 },
        ],
        nb_bobines_par_piste: 2,
        nb_bobines_total: 6,
        quantite_totale_etiq: 10002,
        surprod_etiq: 2,
        q_ajustee: null,
        cout_total_eur: "40.00",
        cout_machine_eur: "20.00",
        cout_mandrins_eur: "20.00",
        mode_mandrins_optimal: "pre_coupe",
      },
    ],
    recommande_cle: "B",
    nb_max_par_bobine: 2239,
    pas_mm: 82,
    alerte_impose: null,
  };
}

function buildResponseImposeImpossible(): PlanificateurBobinesResponse {
  return {
    scenarios: [
      {
        cle: "IMPOSE",
        titre: "Imposé client (3000/bobine)",
        repartition: [
          { nb_etiq_par_bobine: 3000, nb_bobines_par_piste: 2, diametre_mm: 230 },
        ],
        nb_bobines_par_piste: 2,
        nb_bobines_total: 6,
        quantite_totale_etiq: 10002,
        surprod_etiq: 2,
        q_ajustee: null,
        cout_total_eur: null,
        cout_machine_eur: null,
        cout_mandrins_eur: null,
        mode_mandrins_optimal: null,
      },
    ],
    recommande_cle: null,
    nb_max_par_bobine: 2239,
    pas_mm: 82,
    alerte_impose: {
      nb_impose: 3000,
      nb_realisable_max: 2239,
      diametre_requis_mm: 230,
      physiquement_impossible: true,
    },
  };
}

describe("PlanificateurBobines — finition (persistance + Q + forçage)", () => {
  beforeEach(() => {
    routerPushMock.mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("inputs manquants → gate, pas de fetch", async () => {
    installFetchMock(buildResponseSimple());
    render(
      <PlanificateurBobines
        devisId={42}
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={null}
        epaisseurMatiereUm={150}
      />,
    );
    expect(
      screen.getByTestId("plan-bobines-inputs-manquants"),
    ).toBeInTheDocument();
    // On attend un peu (debounce 350ms) — pas d'appel doit avoir lieu.
    await new Promise((r) => setTimeout(r, 500));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("cas type → cartes rendues + badge recommandé sur B", async () => {
    installFetchMock(buildResponseSimple());
    render(
      <PlanificateurBobines
        devisId={42}
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("plan-bobines-card-A")).toBeInTheDocument();
      expect(screen.getByTestId("plan-bobines-card-B")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("plan-bobines-badge-recommande-B"),
    ).toBeInTheDocument();
  });

  it("IMPOSE impossible → bandeau rouge + bloc motif requis", async () => {
    installFetchMock(buildResponseImposeImpossible());
    render(
      <PlanificateurBobines
        devisId={42}
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
      />,
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("plan-bobines-alerte-impose"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("plan-bobines-motif-block")).toBeInTheDocument();
    });
  });

  it("« Choisir » sur scénario B → PUT plan-bobines avec scenario='B'", async () => {
    installFetchMock(buildResponseSimple());
    render(
      <PlanificateurBobines
        devisId={42}
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
      />,
    );
    const btnB = await screen.findByTestId("plan-bobines-btn-B");
    await userEvent.click(btnB);

    await waitFor(() => {
      const putCalls = fetchSpy.mock.calls.filter(
        (c) =>
          String(c[0]).endsWith("/plan-bobines") &&
          (c[1] as RequestInit)?.method === "PUT",
      );
      expect(putCalls.length).toBeGreaterThan(0);
    });
    const putCall = fetchSpy.mock.calls.find(
      (c) =>
        String(c[0]).endsWith("/plan-bobines") &&
        (c[1] as RequestInit)?.method === "PUT",
    );
    const body = JSON.parse((putCall?.[1] as RequestInit).body as string);
    expect(body.scenario).toBe("B");
    expect(body.politique_reliquat).toBe("equilibrees");
    expect(body.force_diametre).toBeNull();
  });

  it("initialSelection → carte restaurée comme sélectionnée", async () => {
    installFetchMock(buildResponseSimple());
    const init: PlanBobinesSelectionIn = {
      scenario: "B",
      nb_bobine: 1667,
      nb_bobines_total: 6,
      politique_reliquat: "equilibrees",
    };
    render(
      <PlanificateurBobines
        devisId={42}
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
        initialSelection={init}
      />,
    );
    const btnB = await screen.findByTestId("plan-bobines-btn-B");
    // Le bouton montre l'état sélectionné.
    expect(btnB).toHaveTextContent(/Sélectionné/);
  });

  it("Forçage IMPOSE : bouton désactivé sans motif, actif avec motif", async () => {
    installFetchMock(buildResponseImposeImpossible());
    render(
      <PlanificateurBobines
        devisId={42}
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
      />,
    );
    const btnForcer = await screen.findByTestId(
      "plan-bobines-btn-forcer-IMPOSE",
    );
    expect(btnForcer).toBeDisabled();

    // Renseigne un motif.
    const motif = screen.getByTestId("plan-bobines-motif-input");
    fireEvent.change(motif, {
      target: { value: "Client accepte les sous-bobines en sortie." },
    });
    expect(btnForcer).not.toBeDisabled();

    // Clic → PUT avec force_diametre=true + motif_forcage rempli.
    await userEvent.click(btnForcer);
    await waitFor(() => {
      const putCalls = fetchSpy.mock.calls.filter(
        (c) =>
          String(c[0]).endsWith("/plan-bobines") &&
          (c[1] as RequestInit)?.method === "PUT",
      );
      expect(putCalls.length).toBeGreaterThan(0);
    });
    const putCall = fetchSpy.mock.calls.find(
      (c) =>
        String(c[0]).endsWith("/plan-bobines") &&
        (c[1] as RequestInit)?.method === "PUT",
    );
    const body = JSON.parse((putCall?.[1] as RequestInit).body as string);
    expect(body.scenario).toBe("IMPOSE");
    expect(body.force_diametre).toBe(true);
    expect(body.motif_forcage).toMatch(/client/i);
  });

  it("« Appliquer cette quantité » sur C → router.push(/optimisation?devis_id=&q=)", async () => {
    // On simule une réponse avec scénario C_sup.
    const resp: PlanificateurBobinesResponse = {
      scenarios: [
        {
          cle: "C_sup",
          titre: "Tomber juste — sup",
          repartition: [
            { nb_etiq_par_bobine: 1667, nb_bobines_par_piste: 2, diametre_mm: 180 },
          ],
          nb_bobines_par_piste: 2,
          nb_bobines_total: 6,
          quantite_totale_etiq: 10002,
          surprod_etiq: 2,
          q_ajustee: 10002,
          cout_total_eur: "40.00",
          cout_machine_eur: "20.00",
          cout_mandrins_eur: "20.00",
          mode_mandrins_optimal: "pre_coupe",
        },
      ],
      recommande_cle: "C_sup",
      nb_max_par_bobine: 2239,
      pas_mm: 82,
      alerte_impose: null,
    };
    installFetchMock(resp);
    render(
      <PlanificateurBobines
        devisId={777}
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
      />,
    );
    const btnQ = await screen.findByTestId("plan-bobines-btn-q-C_sup");
    await userEvent.click(btnQ);
    expect(routerPushMock).toHaveBeenCalledWith(
      "/optimisation?devis_id=777&q=10002",
    );
  });
});
