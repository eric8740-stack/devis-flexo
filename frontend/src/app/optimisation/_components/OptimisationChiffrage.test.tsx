import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import type { Client, OptimisationConfigOut } from "@/lib/api";

import { OptimisationChiffrage } from "./OptimisationChiffrage";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./OptimisationPoseStore";

// Sprint 16 auto-fill — test ciblé : on vérifie que
// OptimisationChiffrage.handleSubmit propage bien
//   - `client_id` (depuis clientSelectionne du store)
//   - `payload_input.sens_enroulement` (depuis sensEnroulementClient)
// au POST /api/devis. Le reste du composant (preview, options, rebobinage
// apply) est mocké au plus court.

// Mock du router Next pour ne pas crasher sur router.push après création.
const routerPushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPushMock }),
}));

// Mock du hook useClientsListe pour fournir une liste minimale.
const useClientsListeMock = vi.fn();
vi.mock("./useClientsListe", () => ({
  useClientsListe: () => useClientsListeMock(),
}));

// ──────────────────────────────────────────────────────────────────
// Fetch mock : route selon l'URL pour retourner la bonne shape.
// ──────────────────────────────────────────────────────────────────
let fetchSpy: ReturnType<typeof vi.fn>;

function installFetchMock(previewErreur?: string) {
  fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : (input as Request).url;
    // Options catalogue tenant.
    if (url.includes("/api/options-disponibles")) {
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => [],
      } as Response;
    }
    // Preview coûts : on retourne un brut/net minimal cohérent, OU un
    // chiffrage incomplet (chiffrage_auto_erreur non-null) si demandé.
    if (url.includes("/api/devis/preview-couts")) {
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () =>
          previewErreur
            ? {
                cout_brut_ht_eur: "0.00",
                reduction_pct: "0",
                reduction_eur: "0.00",
                cout_net_ht_eur: "0.00",
                nb_lots: 1,
                chiffrage_auto_erreur: previewErreur,
              }
            : {
                cout_brut_ht_eur: "1000.00",
                reduction_pct: "0",
                reduction_eur: "0.00",
                cout_net_ht_eur: "1000.00",
                nb_lots: 1,
                chiffrage_auto_erreur: null,
              },
      } as Response;
    }
    // POST /api/devis (création).
    if (
      url.endsWith("/api/devis") &&
      (init?.method ?? "GET").toUpperCase() === "POST"
    ) {
      return {
        ok: true,
        status: 201,
        statusText: "Created",
        json: async () => ({
          id: 999,
          numero: "DEV-2026-0999",
          // …champs minimaux — le composant n'utilise que id + numero.
        }),
      } as Response;
    }
    // applyRebobinageDevis (POST /api/devis/{id}/rebobinage).
    if (
      url.includes("/api/devis/") &&
      url.endsWith("/rebobinage") &&
      (init?.method ?? "GET").toUpperCase() === "POST"
    ) {
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => ({}),
      } as Response;
    }
    throw new Error(`No mock for ${init?.method ?? "GET"} ${url}`);
  });
  global.fetch = fetchSpy as unknown as typeof fetch;
}

function buildClient(): Client {
  return {
    id: 42,
    raison_sociale: "ACME Étiquettes",
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
    diametre_max_bobine_mm: 280,
    nb_etiq_par_bobine_fixe: 2200,
    sens_enroulement: 7,
    marquage_bobine_format: null,
    conditionnement_souhaite: null,
  };
}

function buildFakeCandidat(): OptimisationConfigOut {
  return {
    cylindre_id: 1,
    machine_id: 1,
    nb_poses_dev: 2,
    nb_poses_laize: 5,
    nb_poses_total: 10,
    intervalle_dev_reel_mm: 2,
    intervalle_laize_reel_mm: 2,
    largeur_plaque_mm: 200,
    z_mini_effet_banane: 0,
    qualite_echenillage: "bonne",
    consolidation_atteinte: false,
    intervalle_laize_souhaitable_mm: null,
    disposition_poses: "standard",
    coef_vitesse_echenillage: 1,
    coef_gache_echenillage: 1,
    coef_confort_rayon: 1,
    coef_quinconce: 1,
    coef_consolidation: 1,
    coef_vitesse_options: 1,
    coef_gache_options: 1,
    coef_vitesse_final: 1,
    coef_gache_final: 1,
    score: 100,
    laize_plaque_mm: 200,
    laize_papier_mm: 220,
    chute_laterale_reelle_mm: 10,
    z_cylindre_mm: 330.2,
    nb_dents_cylindre: 104,
    ml_total_m: 1000,
    m2_consomme: 220,
    rendement_pct: 90,
    diametre_bobine_mm: 300,
    laize_liner_mm: 220,
    sens_enroulement: "SE1",
    sens_enroulement_libelle: "Sens 1",
    rotation_vue_a_deg: 0,
    rotation_vue_c_deg: 0,
    machines_compatibles: [1],
    noms_machines_compatibles: ["MA-1"],
    petit_cylindre: false,
    intervalle_laize_recommande_mm: 2,
    intervalle_laize_applique_mm: 2,
    forcage_intervalle_laize: false,
    motif_forcage_intervalle_laize: null,
    intervalle_dev_recommande_mm: 2,
    intervalle_dev_applique_mm: 2,
    forcage_intervalle_dev: false,
    motif_forcage_intervalle_dev: null,
    lacet_droit_mm: 1,
    lacet_gauche_mm: 1,
    lacets_asymetriques: false,
    matiere: null,
    epaisseur_appliquee_um: 150,
    forcage_epaisseur: false,
    motif_forcage_epaisseur: null,
  };
}

/**
 * Wrapper qui configure le store avec :
 *   - 1 candidat sélectionné + quantite + matiere (valide pour submit)
 *   - clientSelectionne = le client passé
 *   - sensEnroulementClient = la valeur passée
 * puis monte OptimisationChiffrage directement (étape "chiffrage").
 */
function setupChiffrage(opts: {
  client: Client | null;
  sensEnroulementOverride?: number | null;
}) {
  function Inner() {
    const {
      goChiffrage,
      goCandidats,
      toggleSelection,
      setQuantiteLot,
      setMatiereLot,
      setClientSelectionne,
      setSensEnroulementClient,
    } = useOptimisationPose();
    useEffect(() => {
      const candidat = buildFakeCandidat();
      goCandidats([candidat], 12000, 100, 80, 76);
      toggleSelection(candidat);
      const idCandidat = `${candidat.cylindre_id}-${candidat.machine_id}-${candidat.nb_poses_dev}x${candidat.nb_poses_laize}-${candidat.sens_enroulement}`;
      setQuantiteLot(idCandidat, 12000);
      setMatiereLot(idCandidat, 1);
      setClientSelectionne(opts.client);
      if (opts.sensEnroulementOverride !== undefined) {
        setSensEnroulementClient(opts.sensEnroulementOverride);
      }
      goChiffrage();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return <OptimisationChiffrage />;
  }
  return render(
    <OptimisationPoseProvider>
      <Inner />
    </OptimisationPoseProvider>,
  );
}

describe("OptimisationChiffrage — Sprint 16 propagation auto-fill", () => {
  beforeEach(() => {
    window.localStorage.clear();
    installFetchMock();
    routerPushMock.mockReset();
    useClientsListeMock.mockReturnValue({
      clients: [buildClient()],
      loading: false,
      error: null,
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("client sélectionné + sens_enroulement profil → POST /api/devis avec client_id et payload_input.sens_enroulement", async () => {
    const client = buildClient();
    setupChiffrage({ client });

    // Attend que le preview résolve + que le bouton submit soit prêt.
    const submitBtn = await screen.findByRole("button", {
      name: /Créer le devis/i,
    });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());

    await userEvent.click(submitBtn);

    // POST /api/devis appelé avec le bon body.
    await waitFor(() => {
      const calls = fetchSpy.mock.calls.filter(
        (c) =>
          String(c[0]).endsWith("/api/devis") &&
          (c[1] as RequestInit)?.method === "POST",
      );
      expect(calls.length).toBeGreaterThan(0);
    });
    const postDevisCall = fetchSpy.mock.calls.find(
      (c) =>
        String(c[0]).endsWith("/api/devis") &&
        (c[1] as RequestInit)?.method === "POST",
    );
    const body = JSON.parse(
      (postDevisCall?.[1] as RequestInit).body as string,
    );
    expect(body.client_id).toBe(42);
    expect(body.payload_input.sens_enroulement).toBe(7);
  });

  it("pas de client sélectionné → client_id null + sens_enroulement null dans payload_input", async () => {
    setupChiffrage({ client: null });

    const submitBtn = await screen.findByRole("button", {
      name: /Créer le devis/i,
    });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    await userEvent.click(submitBtn);

    await waitFor(() => {
      const calls = fetchSpy.mock.calls.filter(
        (c) =>
          String(c[0]).endsWith("/api/devis") &&
          (c[1] as RequestInit)?.method === "POST",
      );
      expect(calls.length).toBeGreaterThan(0);
    });
    const postDevisCall = fetchSpy.mock.calls.find(
      (c) =>
        String(c[0]).endsWith("/api/devis") &&
        (c[1] as RequestInit)?.method === "POST",
    );
    const body = JSON.parse(
      (postDevisCall?.[1] as RequestInit).body as string,
    );
    expect(body.client_id).toBeNull();
    expect(body.payload_input.sens_enroulement).toBeNull();
  });

  it("override sens_enroulement post-auto-fill : la valeur overridée part au POST devis", async () => {
    const client = buildClient(); // sens_enroulement=7 par défaut
    // setClientSelectionne va auto-fill sens=7, puis on override à 2.
    setupChiffrage({ client, sensEnroulementOverride: 2 });

    const submitBtn = await screen.findByRole("button", {
      name: /Créer le devis/i,
    });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    await userEvent.click(submitBtn);

    await waitFor(() => {
      const calls = fetchSpy.mock.calls.filter(
        (c) =>
          String(c[0]).endsWith("/api/devis") &&
          (c[1] as RequestInit)?.method === "POST",
      );
      expect(calls.length).toBeGreaterThan(0);
    });
    const postDevisCall = fetchSpy.mock.calls.find(
      (c) =>
        String(c[0]).endsWith("/api/devis") &&
        (c[1] as RequestInit)?.method === "POST",
    );
    const body = JSON.parse(
      (postDevisCall?.[1] as RequestInit).body as string,
    );
    expect(body.payload_input.sens_enroulement).toBe(2);
  });

  it("preview chiffrage incomplet → bandeau d'erreur, aucun prix affiché (pas de 0,00 €)", async () => {
    // Override du fetch mock : le preview renvoie un chiffrage_auto_erreur.
    installFetchMock(
      "Complexe id=1 (BOPP_BLANC_50) n'a pas de grammage_g_m2 défini, requis pour P1",
    );
    setupChiffrage({ client: null });

    // Le bandeau d'erreur apparaît une fois le preview résolu.
    const bandeau = await screen.findByTestId("chiffrage-erreur-bandeau");
    expect(bandeau).toHaveTextContent(/Chiffrage incomplet/i);
    expect(bandeau).toHaveTextContent(/grammage_g_m2/);

    // Aucun prix « 0,00 € » ne doit être rendu comme un montant valide.
    expect(screen.queryByText(/0,00\s*€/)).not.toBeInTheDocument();
    // Les libellés du récap chiffré ne sont pas montés.
    expect(screen.queryByText(/Coût net HT/i)).not.toBeInTheDocument();
  });
});
