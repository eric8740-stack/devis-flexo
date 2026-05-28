import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { PlanificateurBobinesResponse } from "@/lib/api";

import { PlanificateurBobines } from "./PlanificateurBobines";

// Brief planificateur bobines — on vérifie :
//   1) inputs manquants → gate, pas de fetch
//   2) cas type → 3 scénarios rendus, recommandé visible
//   3) IMPOSE physiquement impossible → bandeau anti-fléau visible

let fetchSpy: ReturnType<typeof vi.fn>;

function installFetchMock(response: PlanificateurBobinesResponse) {
  fetchSpy = vi.fn(async (input: RequestInfo | URL) => {
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
    throw new Error(`No mock for ${url}`);
  });
  global.fetch = fetchSpy as unknown as typeof fetch;
}

describe("PlanificateurBobines", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("inputs manquants → message gate, pas de fetch", async () => {
    installFetchMock({
      scenarios: [],
      recommande_cle: null,
      nb_max_par_bobine: 0,
      pas_mm: 0,
      alerte_impose: null,
    });
    render(
      <PlanificateurBobines
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={null} // manquant
        epaisseurMatiereUm={150}
      />,
    );
    expect(
      screen.getByTestId("plan-bobines-inputs-manquants"),
    ).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("cas type → cartes + badge recommandé visible", async () => {
    installFetchMock({
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
    });
    render(
      <PlanificateurBobines
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    await waitFor(() => {
      expect(screen.getByTestId("plan-bobines-card-A")).toBeInTheDocument();
      expect(screen.getByTestId("plan-bobines-card-B")).toBeInTheDocument();
    });
    // Badge recommandé sur B (coût le plus bas).
    expect(
      screen.getByTestId("plan-bobines-badge-recommande-B"),
    ).toBeInTheDocument();
  });

  it("IMPOSE physiquement impossible → bandeau anti-fléau rouge", async () => {
    installFetchMock({
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
    });
    render(
      <PlanificateurBobines
        quantiteCommandee={10000}
        nLaize={3}
        pasMm={82}
        mandrinMm={76}
        diametreMaxBobineMm={200}
        epaisseurMatiereUm={150}
      />,
    );
    // Simule la saisie d'un nb imposé (déclenche le fetch).
    const input = screen.getByLabelText(/Nb\/bobine imposé/i);
    await act(async () => {
      // setValue via event
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    // L'alerte anti-fléau apparaît (le composant fetch en useEffect dès
    // que les inputs sont OK ; ici on a même un appel sans nb_impose côté
    // input, mais le mock retourne avec alerte_impose dans la réponse).
    await waitFor(() => {
      expect(
        screen.getByTestId("plan-bobines-alerte-impose"),
      ).toBeInTheDocument();
    });
  });
});
