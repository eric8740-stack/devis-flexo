import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import type { CoherenceBobineResponse, Client } from "@/lib/api";

import { CoherenceBobineAlerte } from "./CoherenceBobineAlerte";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./OptimisationPoseStore";

// Brief alerte cohérence Ø ext ↔ nb étiq — on vérifie les 3 cas brief :
//   1) cohérent → severity=ok, pas de warning
//   2) Ø trop petit → severity=warning + Ø requis exposé
//   3) Ø > Dmax client → fit warning séparé
// On mocke fetch pour retourner la réponse backend déterministe.

let fetchSpy: ReturnType<typeof vi.fn>;

function installFetchMock(response: CoherenceBobineResponse) {
  fetchSpy = vi.fn(async (input: RequestInfo | URL) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : (input as Request).url;
    if (url.includes("/api/devis/coherence-bobine")) {
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

function buildClient(): Client {
  return {
    id: 42,
    raison_sociale: "ACME",
    siret: null,
    adresse_fact: null,
    cp_fact: null,
    ville_fact: null,
    contact: null,
    email: null,
    tel: null,
    segment: null,
    date_creation: null,
    marquage_bobine_requis: false,
    mandrin_fourni_par_client: false,
    film_protection_requis: false,
    diametre_mandrin_mm: 40,
    diametre_max_bobine_mm: 200,
    nb_etiq_par_bobine_fixe: 2200,
    sens_enroulement: 7,
    marquage_bobine_format: null,
    conditionnement_souhaite: null,
  };
}

function setup(opts: {
  nbEtiq: number | null;
  diametre: number | null;
  client: Client | null;
  epaisseur: number | null;
}) {
  function Inner() {
    const { setBriefClient, setClientSelectionne } = useOptimisationPose();
    useEffect(() => {
      setBriefClient({
        nb_etiquettes_par_rouleau: opts.nbEtiq,
        diametre_max_bobine_mm: opts.diametre,
      });
      setClientSelectionne(opts.client);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return (
      <CoherenceBobineAlerte
        devEtiqMm={80}
        ecartDevMm={2}
        mandrinMm={76}
        epaisseurCatalogueUm={opts.epaisseur}
      />
    );
  }
  return render(
    <OptimisationPoseProvider>
      <Inner />
    </OptimisationPoseProvider>,
  );
}

describe("CoherenceBobineAlerte", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("severity=ok (cohérent) → bandeau vert, pas de warning", async () => {
    installFetchMock({
      severity: "ok",
      message: "",
      nb_max: 4000,
      diametre_requis_mm: 240,
      fit_severity: null,
      fit_message: null,
      epaisseur_appliquee_um: 150,
      epaisseur_source: "matiere",
    });
    setup({
      nbEtiq: 4000,
      diametre: 240,
      client: null,
      epaisseur: 150,
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    await waitFor(() => {
      expect(screen.getByTestId("coherence-bobine-ok")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("coherence-bobine-warning"),
    ).not.toBeInTheDocument();
  });

  it("Ø trop petit → severity=warning + bandeau ambre avec Ø requis", async () => {
    installFetchMock({
      severity: "warning",
      message:
        "Ø 150 mm permet ≈ 1500 étiq. Tu en as saisi 4000. Ø requis ≈ 242 mm.",
      nb_max: 1500,
      diametre_requis_mm: 242,
      fit_severity: null,
      fit_message: null,
      epaisseur_appliquee_um: 150,
      epaisseur_source: "matiere",
    });
    setup({
      nbEtiq: 4000,
      diametre: 150,
      client: null,
      epaisseur: 150,
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    const warning = await screen.findByTestId("coherence-bobine-warning");
    expect(warning).toHaveTextContent(/permet ≈ 1500/);
    expect(warning).toHaveTextContent(/Ø requis/);
  });

  it("Ø > Dmax client (profil) → fit warning séparé", async () => {
    installFetchMock({
      severity: "ok",
      message: "",
      nb_max: 4000,
      diametre_requis_mm: 240,
      fit_severity: "warning",
      fit_message: "Ø 240 mm > Ø max machine de pose (200 mm) : la bobine ne rentre pas.",
      epaisseur_appliquee_um: 150,
      epaisseur_source: "matiere",
    });
    setup({
      nbEtiq: 4000,
      diametre: 240,
      client: buildClient(),
      epaisseur: 150,
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    const fit = await screen.findByTestId("coherence-bobine-fit-warning");
    expect(fit).toHaveTextContent(/ne rentre pas/);
  });

  it("inputs incomplets → aucun render (pas d'appel API)", async () => {
    installFetchMock({
      severity: "ok",
      message: "",
      nb_max: 0,
      diametre_requis_mm: 0,
      fit_severity: null,
      fit_message: null,
      epaisseur_appliquee_um: 150,
      epaisseur_source: "fallback",
    });
    setup({
      nbEtiq: null, // manquant
      diametre: 240,
      client: null,
      epaisseur: null,
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(
      screen.queryByTestId("coherence-bobine-alerte"),
    ).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
