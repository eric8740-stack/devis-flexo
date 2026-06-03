import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import type {
  Client,
  OptimisationConfigOut,
  RebobinageCalculerRequest,
  RebobinageMultilotsRequest,
  RebobinageResultat,
} from "@/lib/api";

import { OptimisationChiffrage } from "./OptimisationChiffrage";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
  type LotDiametreEcho,
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
    // applyRebobinageMultilotsDevis (POST /api/devis/{id}/rebobinage-multilots).
    if (
      url.includes("/api/devis/") &&
      url.endsWith("/rebobinage-multilots") &&
      (init?.method ?? "GET").toUpperCase() === "POST"
    ) {
      return {
        ok: true,
        status: 200,
        statusText: "OK",
        json: async () => ({
          machine_rebobineuse_id: 1,
          nb_lots: 1,
          cout_total_rebobinage_eur: "10.00",
          cout_mandrins_eur: "1.00",
          lots: [],
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
  nbCouleursImpression?: number;
  // Bug #6 (6.2c) — écho rebobinage multi-lots à injecter pour le lot unique.
  echo?: LotDiametreEcho;
  // Bug #6 (6.2e) — requests rebobinage à propager au store (apply au submit).
  rebobinageMultilots?: RebobinageMultilotsRequest;
  rebobinageMono?: { req: RebobinageCalculerRequest; result: RebobinageResultat };
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
      setNbCouleursImpression,
      setDiametreEchoesParLot,
      setRebobinage,
      setRebobinageMultilotsRequest,
    } = useOptimisationPose();
    useEffect(() => {
      const candidat = buildFakeCandidat();
      goCandidats([candidat], 12000, 100, 80, 76);
      toggleSelection(candidat);
      const idCandidat = `${candidat.cylindre_id}-${candidat.machine_id}-${candidat.nb_poses_dev}x${candidat.nb_poses_laize}-${candidat.sens_enroulement}`;
      setQuantiteLot(idCandidat, 12000);
      setMatiereLot(idCandidat, 1);
      if (opts.echo) {
        setDiametreEchoesParLot({ [idCandidat]: opts.echo });
      }
      if (opts.rebobinageMono) {
        setRebobinage(opts.rebobinageMono.req, opts.rebobinageMono.result);
      }
      if (opts.rebobinageMultilots) {
        setRebobinageMultilotsRequest(opts.rebobinageMultilots);
      }
      setClientSelectionne(opts.client);
      if (opts.sensEnroulementOverride !== undefined) {
        setSensEnroulementClient(opts.sensEnroulementOverride);
      }
      if (opts.nbCouleursImpression !== undefined) {
        setNbCouleursImpression(opts.nbCouleursImpression);
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

  it("nb_couleurs impression du store → payload_input.nb_couleurs (pantone/blanc/vernis à 0) au POST devis", async () => {
    setupChiffrage({ client: null, nbCouleursImpression: 6 });

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
    expect(body.payload_input.nb_couleurs).toEqual({
      impression: 6,
      pantone: 0,
      blanc: 0,
      vernis: 0,
    });
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

  // ──────────────────────────────────────────────────────────────────
  // Bug #6 (6.2c) — enrichissement de payload_visuel par les échos rebobinage
  // ──────────────────────────────────────────────────────────────────

  function findPostDevisBody() {
    const call = fetchSpy.mock.calls.find(
      (c) =>
        String(c[0]).endsWith("/api/devis") &&
        (c[1] as RequestInit)?.method === "POST",
    );
    return JSON.parse((call?.[1] as RequestInit).body as string);
  }

  it("écho rebobinage présent → payload_visuel enrichi du Ø réel par lot au POST devis", async () => {
    setupChiffrage({
      client: null,
      echo: {
        diametre_bobine_mm: 305,
        diametre_depart_mm: 82,
        epaisseur_effective_um: 90,
        epaisseur_source: "matiere",
        paroi_mm: 3,
        nb_bobines: 7,
      },
    });

    const submitBtn = await screen.findByRole("button", {
      name: /Créer le devis/i,
    });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    await userEvent.click(submitBtn);

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(
          (c) =>
            String(c[0]).endsWith("/api/devis") &&
            (c[1] as RequestInit)?.method === "POST",
        ),
      ).toBe(true),
    );
    const pv = findPostDevisBody().lots[0].payload_visuel;
    expect(pv.diametre_bobine_mm).toBe(305); // écrasé par l'écho (était 300)
    expect(pv.diametre_depart_mm).toBe(82);
    expect(pv.epaisseur_effective_um).toBe(90);
    expect(pv.epaisseur_source).toBe("matiere");
    expect(pv.paroi_mm).toBe(3);
    expect(pv.nb_bobines_rebobinage).toBe(7);
  });

  it("pas d'écho rebobinage → payload_visuel = candidat figé (fallback non-régressif)", async () => {
    setupChiffrage({ client: null });

    const submitBtn = await screen.findByRole("button", {
      name: /Créer le devis/i,
    });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    await userEvent.click(submitBtn);

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(
          (c) =>
            String(c[0]).endsWith("/api/devis") &&
            (c[1] as RequestInit)?.method === "POST",
        ),
      ).toBe(true),
    );
    const pv = findPostDevisBody().lots[0].payload_visuel;
    expect(pv.diametre_bobine_mm).toBe(300); // candidat figé inchangé
    expect(pv.epaisseur_source).toBeUndefined();
    expect(pv.diametre_depart_mm).toBeUndefined();
  });

  // ──────────────────────────────────────────────────────────────────
  // Bug #6 (6.2e) — apply rebobinage via l'endpoint MULTI-LOTS
  // ──────────────────────────────────────────────────────────────────

  const TARIFS = {
    prix_pre_coupe_par_mandrin_eur: "0.50",
    cout_decoupe_interne_par_mandrin_eur: "0.15",
    cout_fixe_decoupe_interne_eur: "5.00",
  };

  function buildMultilotsReq(): RebobinageMultilotsRequest {
    return {
      lots: [
        {
          nb_etiquettes_total: 12000,
          intervalle_developpe_mm: "2",
          diametre_mandrin_mm: 76,
          diametre_max_bobine_mm: 300,
          nb_etiq_par_bobine_fixe: null,
          matiere_id: 1,
          epaisseur_saisie_um: null,
          paroi_override_mm: 5,
        },
      ],
      machine_rebobineuse_id: 1,
      tarifs_mandrins: TARIFS,
      mode: "auto",
      motif_force: null,
    };
  }

  function buildMonoReq(): {
    req: RebobinageCalculerRequest;
    result: RebobinageResultat;
  } {
    return {
      req: {
        spec_lot: {
          nb_etiquettes_total: 12000,
          intervalle_developpe_mm: "2",
          epaisseur_matiere_mm: "0.15",
        },
        profil_client: {
          diametre_mandrin_mm: 76,
          diametre_max_bobine_mm: 300,
          nb_etiq_par_bobine_fixe: null,
        },
        machine_rebobineuse_id: 1,
        tarifs_mandrins: TARIFS,
        mode: "auto",
        motif_force: null,
      },
      result: {
        bobines: {
          nb_etiq_par_bobine: 1500,
          nb_bobines: 8,
          bobine_partielle: false,
          nb_etiq_derniere_bobine: 1500,
          longueur_totale_m: "960.00",
        },
        temps: {
          temps_roulage_min: "12.50",
          temps_changements_min: "12.00",
          temps_total_min: "24.50",
          cout_machine_eur: "18.38",
        },
        arbitrage: {
          mode_optimal: "decoupe_interne",
          cout_pre_coupe_total_eur: "22.38",
          cout_decoupe_interne_total_eur: "20.18",
          ecart_pct: "10.9",
          mode_applique: "decoupe_interne",
          motif_force: null,
        },
        cout_mandrins_eur: "1.80",
        cout_total_rebobinage_eur: "20.18",
        machine_rebobineuse_id: 1,
      },
    };
  }

  const isPost = (c: unknown[]) =>
    (c[1] as RequestInit)?.method === "POST";

  it("request multi-lots présent → apply via POST /api/devis/{id}/rebobinage-multilots", async () => {
    setupChiffrage({ client: null, rebobinageMultilots: buildMultilotsReq() });

    const submitBtn = await screen.findByRole("button", {
      name: /Créer le devis/i,
    });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    await userEvent.click(submitBtn);

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(
          (c) =>
            String(c[0]).endsWith("/rebobinage-multilots") && isPost(c),
        ),
      ).toBe(true),
    );
    const call = fetchSpy.mock.calls.find(
      (c) => String(c[0]).endsWith("/rebobinage-multilots") && isPost(c),
    );
    const body = JSON.parse((call![1] as RequestInit).body as string);
    expect(body.lots[0].paroi_override_mm).toBe(5);
    expect(body.lots[0].matiere_id).toBe(1);
    // Le chemin mono-lot ne doit PAS être appelé.
    expect(
      fetchSpy.mock.calls.some(
        (c) => String(c[0]).endsWith("/rebobinage") && isPost(c),
      ),
    ).toBe(false);
  });

  it("pas de multi-lots, mono présent → fallback POST /api/devis/{id}/rebobinage (non-régressif)", async () => {
    setupChiffrage({ client: null, rebobinageMono: buildMonoReq() });

    const submitBtn = await screen.findByRole("button", {
      name: /Créer le devis/i,
    });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    await userEvent.click(submitBtn);

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(
          (c) => String(c[0]).endsWith("/rebobinage") && isPost(c),
        ),
      ).toBe(true),
    );
    // L'endpoint multi-lots ne doit PAS être appelé en fallback.
    expect(
      fetchSpy.mock.calls.some(
        (c) => String(c[0]).endsWith("/rebobinage-multilots") && isPost(c),
      ),
    ).toBe(false);
  });
});
