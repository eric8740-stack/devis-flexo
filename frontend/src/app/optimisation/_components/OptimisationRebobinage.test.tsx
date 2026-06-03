import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import type {
  Client,
  OptimisationConfigOut,
  RebobinageMultilotsResponse,
  RebobinageResultat,
} from "@/lib/api";

import { OptimisationRebobinage } from "./OptimisationRebobinage";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./OptimisationPoseStore";
import type { MachineRebobineuseLite } from "./useRebobineusesDuTenant";

// Mock du hook useRebobineusesDuTenant — permet d'injecter les 3 cas
// (1 machine, N machines, 0 machine) sans dépendre du placeholder du
// hook. Le câblage final remplacera le corps du hook par un fetch ;
// la signature de retour testée ici restera identique.
const useRebobineusesMock = vi.fn();
vi.mock("./useRebobineusesDuTenant", () => ({
  useRebobineusesDuTenant: () => useRebobineusesMock(),
}));

// Mock du hook useClientsListe — par défaut liste vide (= comportement
// "pas de client", préserve les tests existants). Les tests d'auto-fill
// Sprint 16 surchargent via mockReturnValue pour injecter des clients.
const useClientsListeMock = vi.fn();
vi.mock("./useClientsListe", () => ({
  useClientsListe: () => useClientsListeMock(),
}));

function buildClient(overrides: Partial<Client> = {}): Client {
  return {
    id: 1,
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
    diametre_mandrin_mm: null,
    diametre_max_bobine_mm: null,
    nb_etiq_par_bobine_fixe: null,
    sens_enroulement: null,
    marquage_bobine_format: null,
    conditionnement_souhaite: null,
    ...overrides,
  };
}

function machine(
  id: number,
  nom: string,
  actif = true,
): MachineRebobineuseLite {
  // Defaults raisonnables pour les champs qui ne pilotent pas les
  // assertions des tests (marque/modele/laize_max_mm/diametre_max_mm).
  return {
    id,
    nom,
    actif,
    marque: null,
    modele: null,
    laize_max_mm: "250.00",
    diametre_max_mm: 500,
  };
}

// Sprint 16 Lot D câblage — tests de non-régression du composant après
// remplacement des mocks par l'API réelle (POST /api/rebobinage/calculer).
// Couvre les deux invariants critiques :
//   1. Pré-remplissage des champs bobine depuis le brief client (store).
//   2. Forçage commercial du mode → motif obligatoire (validation
//      bloquante avant passage à l'étape chiffrage).

// ──────────────────────────────────────────────────────────────────
// Mock fetch — retourne un résultat rebobinage par défaut. Les tests
// individuels peuvent surcharger via fetchSpy.mockResolvedValueOnce.
// ──────────────────────────────────────────────────────────────────
function buildResultat(
  overrides: Partial<RebobinageResultat> = {},
): RebobinageResultat {
  return {
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
    ...overrides,
  };
}

// Bug #6 (6.2) — réponse multi-lots par défaut (1 entrée par lot). Les tests
// surchargent `lots` pour piloter Ø / nb bobines / source d'épaisseur.
function buildMultilotsResponse(
  overrides: Partial<RebobinageMultilotsResponse> = {},
): RebobinageMultilotsResponse {
  return {
    lots: [
      {
        epaisseur_effective_um: 90,
        epaisseur_source: "matiere",
        mandrin_mm: 76,
        paroi_mm: 3,
        diametre_depart_mm: 82,
        diametre_bobine_mm: 305,
        rebobinage: buildResultat(),
      },
    ],
    ...overrides,
  };
}

let fetchSpy: ReturnType<typeof vi.fn>;

// Mock fetch URL-aware : le composant appelle MAINTENANT deux endpoints
// (`/api/rebobinage/calculer` mono-lot conservé + `/api/rebobinage/
// calculer-multilots` pour le Ø par lot). On route chaque URL vers la bonne
// forme de réponse pour ne pas casser les assertions mono-lot existantes.
function installFetchMock(
  defaultResult: RebobinageResultat = buildResultat(),
  multilotsResult: RebobinageMultilotsResponse = buildMultilotsResponse(),
) {
  fetchSpy = vi.fn(async (url: unknown) => {
    const body = String(url).includes("/api/rebobinage/calculer-multilots")
      ? multilotsResult
      : defaultResult;
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => body,
    };
  });
  global.fetch = fetchSpy as unknown as typeof fetch;
}

/**
 * Wrapper de test : configure le store + bascule sur l'étape "rebobinage"
 * avant de monter OptimisationRebobinage. Permet d'injecter un brief
 * client et un candidat sélectionné réalistes.
 */
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

function setupRebobinage(opts: {
  briefClient?: {
    nb_etiquettes_par_rouleau?: number | null;
    diametre_max_bobine_mm?: number | null;
  };
  mandrinInitial?: number;
  // Sprint 16 — client pré-sélectionné dans le store avant le mount
  // de OptimisationRebobinage (simule le sélecteur déjà utilisé OU
  // l'hydratation depuis un devis existant).
  clientInitial?: Client | null;
}) {
  function Inner() {
    const {
      etape,
      goRebobinage,
      setBriefClient,
      goCandidats,
      toggleSelection,
      setQuantiteLot,
      setMatiereLot,
      setClientSelectionne,
    } = useOptimisationPose();
    useEffect(() => {
      if (opts.briefClient) setBriefClient(opts.briefClient);
      if (opts.clientInitial !== undefined) {
        setClientSelectionne(opts.clientInitial);
      }
      const candidat = buildFakeCandidat();
      goCandidats([candidat], 12000, 100, 80, opts.mandrinInitial ?? 76);
      toggleSelection(candidat);
      // Hydrate quantite + matiere pour passer les checks de l'étape detail.
      const idCandidat = `${candidat.cylindre_id}-${candidat.machine_id}-${candidat.nb_poses_dev}x${candidat.nb_poses_laize}-${candidat.sens_enroulement}`;
      setQuantiteLot(idCandidat, 12000);
      setMatiereLot(idCandidat, 1);
      goRebobinage();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    if (etape !== "rebobinage") return null;
    return <OptimisationRebobinage />;
  }
  return render(
    <OptimisationPoseProvider>
      <Inner />
    </OptimisationPoseProvider>,
  );
}

/**
 * Variante avec spy de l'étape + spy du request rebobinage propagé au
 * store. Permet de vérifier la navigation après "Continuer".
 */
function setupRebobinageAvecSpyEtape() {
  function EtapeSpy() {
    const { etape, rebobinageRequest } = useOptimisationPose();
    return (
      <>
        <div data-testid="etape-courante">{etape}</div>
        <div data-testid="rebobinage-request-mode">
          {rebobinageRequest ? rebobinageRequest.mode : "absent"}
        </div>
      </>
    );
  }
  function Inner() {
    const {
      etape,
      goRebobinage,
      goCandidats,
      toggleSelection,
      setQuantiteLot,
      setMatiereLot,
      setBriefClient,
    } = useOptimisationPose();
    useEffect(() => {
      // diametre_max_bobine_mm défini pour que le composant puisse calculer.
      setBriefClient({ diametre_max_bobine_mm: 300 });
      const candidat = buildFakeCandidat();
      goCandidats([candidat], 12000, 100, 80, 76);
      toggleSelection(candidat);
      const idCandidat = `${candidat.cylindre_id}-${candidat.machine_id}-${candidat.nb_poses_dev}x${candidat.nb_poses_laize}-${candidat.sens_enroulement}`;
      setQuantiteLot(idCandidat, 12000);
      setMatiereLot(idCandidat, 1);
      goRebobinage();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return (
      <>
        <EtapeSpy />
        {etape === "rebobinage" && <OptimisationRebobinage />}
      </>
    );
  }
  return render(
    <OptimisationPoseProvider>
      <Inner />
    </OptimisationPoseProvider>,
  );
}

describe("OptimisationRebobinage — Sprint 16 Lot D câblage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    installFetchMock();
    // Par défaut : 1 rebobineuse — comportement attendu par les tests
    // existants (auto-sélection, pas de picker). Les tests "fin du
    // hardcode id=1" plus bas surchargent via mockReturnValue.
    useRebobineusesMock.mockReturnValue({
      machines: [machine(1, "Daco D250")],
      loading: false,
      error: null,
    });
    // Par défaut : liste clients vide — préserve les tests existants
    // qui ne testent pas l'auto-fill. Les tests Sprint 16 auto-fill
    // surchargent via useClientsListeMock.mockReturnValue.
    useClientsListeMock.mockReturnValue({
      clients: [],
      loading: false,
      error: null,
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("pré-remplit Ø max bobine, nb étiq/bobine et Ø mandrin depuis le store", async () => {
    setupRebobinage({
      briefClient: {
        nb_etiquettes_par_rouleau: 1500,
        diametre_max_bobine_mm: 250,
      },
      mandrinInitial: 40,
    });

    const diamMax = (await screen.findByLabelText(
      /Ø Max bobine livrée/i,
    )) as HTMLInputElement;
    const nbEtiq = screen.getByLabelText(
      /Nb étiquettes \/ bobine/i,
    ) as HTMLInputElement;
    const mandrin = screen.getByLabelText(
      /Ø Mandrin bobine/i,
    ) as HTMLSelectElement;

    expect(diamMax.value).toBe("250");
    expect(nbEtiq.value).toBe("1500");
    expect(mandrin.value).toBe("40");

    // Le composant déclenche un calcul initial dès qu'il a un Ø max valide.
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const firstCall = fetchSpy.mock.calls[0]?.[0] as string;
    expect(firstCall).toContain("/api/rebobinage/calculer");
  });

  it("pas de brief client → inputs vides + mandrin par défaut, pas de calcul auto", async () => {
    setupRebobinage({});

    const diamMax = (await screen.findByLabelText(
      /Ø Max bobine livrée/i,
    )) as HTMLInputElement;
    const nbEtiq = screen.getByLabelText(
      /Nb étiquettes \/ bobine/i,
    ) as HTMLInputElement;
    const mandrin = screen.getByLabelText(
      /Ø Mandrin bobine/i,
    ) as HTMLSelectElement;

    expect(diamMax.value).toBe("");
    expect(nbEtiq.value).toBe("");
    expect(mandrin.value).toBe("76");
    // Sans Ø max, buildRequest renvoie null → pas d'auto-calcul.
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forçage mode sans motif : erreur affichée, étape reste 'rebobinage', store rebobinage absent", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("forcer-mode-checkbox");

    await userEvent.click(screen.getByTestId("forcer-mode-checkbox"));
    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    expect(screen.getByTestId("motif-erreur")).toHaveTextContent(
      /Motif obligatoire/i,
    );
    expect(screen.getByTestId("etape-courante")).toHaveTextContent(
      "rebobinage",
    );
    // Le request n'a pas été propagé au store puisqu'on n'a pas continué.
    expect(screen.getByTestId("rebobinage-request-mode")).toHaveTextContent(
      "absent",
    );
  });

  it("forçage mode + motif trop court (<10 chars) : erreur, pas de passage chiffrage", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("forcer-mode-checkbox");

    await userEvent.click(screen.getByTestId("forcer-mode-checkbox"));
    await userEvent.type(screen.getByTestId("motif-force-textarea"), "court");
    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    expect(screen.getByTestId("motif-erreur")).toBeInTheDocument();
    expect(screen.getByTestId("etape-courante")).toHaveTextContent(
      "rebobinage",
    );
  });

  it("forçage mode + motif valide : POST /api/rebobinage/calculer avec mode+motif, passage 'chiffrage', store propagé", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("forcer-mode-checkbox");

    await userEvent.click(screen.getByTestId("forcer-mode-checkbox"));
    await userEvent.type(
      screen.getByTestId("motif-force-textarea"),
      "Contrainte client export Asie urgence",
    );
    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    await waitFor(() =>
      expect(screen.getByTestId("etape-courante")).toHaveTextContent(
        "chiffrage",
      ),
    );
    expect(screen.queryByTestId("motif-erreur")).toBeNull();
    // Le store a été mis à jour avec le mode forcé (= "pre_coupe" par défaut
    // dans le composant quand on coche forcer sans changer le select).
    expect(screen.getByTestId("rebobinage-request-mode")).toHaveTextContent(
      "pre_coupe",
    );

    // Vérifier qu'un appel POST a bien envoyé mode=pre_coupe + motif.
    const calls = fetchSpy.mock.calls;
    const lastCall = calls[calls.length - 1];
    const lastInit = lastCall?.[1] as RequestInit;
    const lastBody = JSON.parse(lastInit.body as string);
    expect(lastBody.mode).toBe("pre_coupe");
    expect(lastBody.motif_force).toContain("Contrainte client");
  });

  it("pas de forçage : POST /api/rebobinage/calculer avec mode='auto', passage 'chiffrage'", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("rebobinage-continuer");

    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    await waitFor(() =>
      expect(screen.getByTestId("etape-courante")).toHaveTextContent(
        "chiffrage",
      ),
    );
    expect(screen.getByTestId("rebobinage-request-mode")).toHaveTextContent(
      "auto",
    );
    // Le dernier appel (recalcul final avant passage chiffrage) doit avoir
    // mode=auto + motif_force=null.
    const calls = fetchSpy.mock.calls;
    const lastCall = calls[calls.length - 1];
    const lastInit = lastCall?.[1] as RequestInit;
    const lastBody = JSON.parse(lastInit.body as string);
    expect(lastBody.mode).toBe("auto");
    expect(lastBody.motif_force).toBeNull();
  });

  it("affiche le résultat retourné par l'API (nb bobines, coût total)", async () => {
    installFetchMock(
      buildResultat({
        bobines: {
          nb_etiq_par_bobine: 2000,
          nb_bobines: 6,
          bobine_partielle: false,
          nb_etiq_derniere_bobine: 2000,
          longueur_totale_m: "720.00",
        },
        cout_total_rebobinage_eur: "15.42",
      }),
    );
    setupRebobinage({
      briefClient: { diametre_max_bobine_mm: 300 },
    });

    await waitFor(() =>
      expect(screen.getByTestId("calcul-nb-bobines")).toHaveTextContent("6"),
    );
    expect(screen.getByTestId("calcul-cout")).toHaveTextContent("15,42");
  });

  // ──────────────────────────────────────────────────────────────────
  // Sélection rebobineuse — fin du hardcode id=1
  // ──────────────────────────────────────────────────────────────────

  it("1 rebobineuse : affichage lecture seule, pas de picker, id envoyé au calcul = id réel du tenant", async () => {
    useRebobineusesMock.mockReturnValue({
      machines: [machine(42, "Karlville K200 (tenant XYZ)")],
      loading: false,
      error: null,
    });
    setupRebobinage({
      briefClient: { diametre_max_bobine_mm: 300 },
    });

    // Lecture seule + nom de la machine visible.
    expect(
      await screen.findByTestId("rebobineuse-unique"),
    ).toHaveTextContent("Karlville K200 (tenant XYZ)");
    expect(screen.queryByTestId("rebobineuse-select")).toBeNull();

    // Le 1er fetch doit utiliser l'id réel (42), pas 1 hardcodé.
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const firstInit = fetchSpy.mock.calls[0]?.[1] as RequestInit;
    const firstBody = JSON.parse(firstInit.body as string);
    expect(firstBody.machine_rebobineuse_id).toBe(42);
  });

  it("N rebobineuses : picker rendu, sélection d'une autre machine envoie son id au prochain calcul", async () => {
    useRebobineusesMock.mockReturnValue({
      machines: [
        machine(10, "Daco D250"),
        machine(11, "Karlville K200"),
        machine(12, "GM rebobineuse"),
      ],
      loading: false,
      error: null,
    });
    setupRebobinage({
      briefClient: { diametre_max_bobine_mm: 300 },
    });

    const select = (await screen.findByTestId(
      "rebobineuse-select",
    )) as HTMLSelectElement;
    expect(select.options).toHaveLength(3);
    // Auto-sélection sur la 1ère machine.
    expect(select.value).toBe("10");

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const firstBody = JSON.parse(
      (fetchSpy.mock.calls[0]?.[1] as RequestInit).body as string,
    );
    expect(firstBody.machine_rebobineuse_id).toBe(10);

    // Bascule sur la 3e rebobineuse → re-calcul auto avec id=12.
    await userEvent.selectOptions(select, "12");
    await waitFor(() => expect(fetchSpy.mock.calls.length).toBeGreaterThan(1));
    const lastBody = JSON.parse(
      (fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1]?.[1] as RequestInit)
        .body as string,
    );
    expect(lastBody.machine_rebobineuse_id).toBe(12);
  });

  it("0 rebobineuse : message clair, calcul ne part pas, bouton Continuer désactivé", async () => {
    useRebobineusesMock.mockReturnValue({
      machines: [],
      loading: false,
      error: null,
    });
    setupRebobinage({
      briefClient: { diametre_max_bobine_mm: 300 },
    });

    expect(
      await screen.findByTestId("aucune-rebobineuse"),
    ).toHaveTextContent(/Aucune rebobineuse configurée/i);
    // Pas de fetch déclenché tant qu'il n'y a pas de machine.
    expect(fetchSpy).not.toHaveBeenCalled();
    // Le bouton "Continuer vers chiffrage" doit être désactivé.
    const continuer = screen.getByTestId(
      "rebobinage-continuer",
    ) as HTMLButtonElement;
    expect(continuer).toBeDisabled();
  });

  // ──────────────────────────────────────────────────────────────────
  // Sprint 16 auto-fill — profil rebobinage client
  // ──────────────────────────────────────────────────────────────────

  it("auto-fill : profil client rempli prend priorité sur le brief client (3 numériques + sens_enroulement)", async () => {
    // Brief client distinct du profil → on prouve que le profil prime.
    const client = buildClient({
      id: 42,
      diametre_mandrin_mm: 40,
      diametre_max_bobine_mm: 280,
      nb_etiq_par_bobine_fixe: 2200,
      sens_enroulement: 4,
    });
    useClientsListeMock.mockReturnValue({
      clients: [client],
      loading: false,
      error: null,
    });
    setupRebobinage({
      briefClient: {
        nb_etiquettes_par_rouleau: 9999, // ignoré au profit du profil
        diametre_max_bobine_mm: 600, // ignoré au profit du profil
      },
      mandrinInitial: 76, // ignoré au profit du profil
      clientInitial: client,
    });

    // Les 3 numériques prennent les valeurs profil, pas brief / saisie.
    const diamMax = (await screen.findByLabelText(
      /Ø Max bobine livrée/i,
    )) as HTMLInputElement;
    const nbEtiq = screen.getByLabelText(
      /Nb étiquettes \/ bobine/i,
    ) as HTMLInputElement;
    const mandrin = screen.getByLabelText(
      /Ø Mandrin bobine/i,
    ) as HTMLSelectElement;
    expect(diamMax.value).toBe("280");
    expect(nbEtiq.value).toBe("2200");
    expect(mandrin.value).toBe("40");

    // sens_enroulement profil pré-rempli dans l'input dédié.
    const sens = screen.getByTestId(
      "sens-enroulement-input",
    ) as HTMLInputElement;
    expect(sens.value).toBe("4");
  });

  it("auto-fill + override : la valeur overridée part au POST /api/rebobinage/calculer (pas la valeur profil)", async () => {
    const client = buildClient({
      id: 42,
      diametre_mandrin_mm: 40,
      diametre_max_bobine_mm: 280,
      nb_etiq_par_bobine_fixe: 2200,
    });
    useClientsListeMock.mockReturnValue({
      clients: [client],
      loading: false,
      error: null,
    });
    setupRebobinage({
      briefClient: { diametre_max_bobine_mm: 600 },
      clientInitial: client,
    });

    const diamMax = (await screen.findByLabelText(
      /Ø Max bobine livrée/i,
    )) as HTMLInputElement;
    await waitFor(() => expect(diamMax.value).toBe("280"));

    // Override : on remplace 280 par 350.
    await userEvent.clear(diamMax);
    await userEvent.type(diamMax, "350");

    // Recalcul manuel pour vérifier le body envoyé.
    await userEvent.click(screen.getByTestId("rebobinage-recalculer"));
    // endsWith pour cibler le mono-lot `/calculer` SANS matcher
    // `/calculer-multilots` (qui contient la même sous-chaîne).
    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.find((c) =>
          String(c[0]).endsWith("/api/rebobinage/calculer"),
        ),
      ).toBeTruthy(),
    );
    const lastCalc = [...fetchSpy.mock.calls]
      .reverse()
      .find((c) => String(c[0]).endsWith("/api/rebobinage/calculer"));
    const body = JSON.parse((lastCalc?.[1] as RequestInit).body as string);
    expect(body.profil_client.diametre_max_bobine_mm).toBe(350);
  });

  it("pas de client sélectionné : aucun auto-fill, comportement actuel préservé (brief + saisie)", async () => {
    // Pas de clientInitial → comportement Lot D : auto-fill depuis brief +
    // saisie étape 1 uniquement.
    setupRebobinage({
      briefClient: {
        nb_etiquettes_par_rouleau: 1500,
        diametre_max_bobine_mm: 250,
      },
      mandrinInitial: 40,
    });

    const diamMax = (await screen.findByLabelText(
      /Ø Max bobine livrée/i,
    )) as HTMLInputElement;
    const nbEtiq = screen.getByLabelText(
      /Nb étiquettes \/ bobine/i,
    ) as HTMLInputElement;
    const mandrin = screen.getByLabelText(
      /Ø Mandrin bobine/i,
    ) as HTMLSelectElement;
    expect(diamMax.value).toBe("250");
    expect(nbEtiq.value).toBe("1500");
    expect(mandrin.value).toBe("40");

    // Pas de bandeau exigences (pas de client).
    expect(screen.queryByTestId("exigences-client-bandeau")).toBeNull();
    // L'input sens enroulement est vide (pas de profil).
    const sens = screen.getByTestId(
      "sens-enroulement-input",
    ) as HTMLInputElement;
    expect(sens.value).toBe("");
  });

  it("bandeau exigences : visible si au moins une exigence client renseignée, masqué sinon", async () => {
    // 1. Client SANS aucune exigence : bandeau absent.
    const clientVide = buildClient({ id: 1, diametre_max_bobine_mm: 300 });
    useClientsListeMock.mockReturnValue({
      clients: [clientVide],
      loading: false,
      error: null,
    });
    const { unmount } = setupRebobinage({ clientInitial: clientVide });
    await screen.findByTestId("client-section");
    expect(screen.queryByTestId("exigences-client-bandeau")).toBeNull();
    unmount();

    // 2. Client AVEC exigences : bandeau visible avec les bonnes lignes.
    const clientExigeant = buildClient({
      id: 2,
      diametre_max_bobine_mm: 300,
      marquage_bobine_requis: true,
      film_protection_requis: true,
      mandrin_fourni_par_client: false, // false → pas dans la liste
      marquage_bobine_format: "Étiquette A6",
      conditionnement_souhaite: null, // null → pas dans la liste
    });
    useClientsListeMock.mockReturnValue({
      clients: [clientExigeant],
      loading: false,
      error: null,
    });
    setupRebobinage({ clientInitial: clientExigeant });

    const bandeau = await screen.findByTestId("exigences-client-bandeau");
    expect(
      within(bandeau).getByTestId("exigence-marquage"),
    ).toBeInTheDocument();
    expect(
      within(bandeau).getByTestId("exigence-film"),
    ).toBeInTheDocument();
    expect(
      within(bandeau).getByTestId("exigence-marquage-format"),
    ).toHaveTextContent("Étiquette A6");
    // Booléens à false ou textes null → absents du bandeau.
    expect(
      within(bandeau).queryByTestId("exigence-mandrin"),
    ).toBeNull();
    expect(
      within(bandeau).queryByTestId("exigence-conditionnement"),
    ).toBeNull();
  });

  it("sens_enroulement : pré-rempli depuis le profil → présent dans le store, override propagé", async () => {
    // Spy sur sensEnroulementClient du store via un sous-composant.
    function SensSpy() {
      const { sensEnroulementClient } = useOptimisationPose();
      return (
        <div data-testid="store-sens">
          {sensEnroulementClient === null ? "null" : String(sensEnroulementClient)}
        </div>
      );
    }
    const client = buildClient({
      id: 5,
      diametre_max_bobine_mm: 300,
      sens_enroulement: 7,
    });
    useClientsListeMock.mockReturnValue({
      clients: [client],
      loading: false,
      error: null,
    });

    function Inner() {
      const {
        etape,
        goRebobinage,
        goCandidats,
        toggleSelection,
        setQuantiteLot,
        setMatiereLot,
        setClientSelectionne,
      } = useOptimisationPose();
      useEffect(() => {
        setClientSelectionne(client);
        const candidat = buildFakeCandidat();
        goCandidats([candidat], 12000, 100, 80, 76);
        toggleSelection(candidat);
        const idCandidat = `${candidat.cylindre_id}-${candidat.machine_id}-${candidat.nb_poses_dev}x${candidat.nb_poses_laize}-${candidat.sens_enroulement}`;
        setQuantiteLot(idCandidat, 12000);
        setMatiereLot(idCandidat, 1);
        goRebobinage();
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return (
        <>
          <SensSpy />
          {etape === "rebobinage" && <OptimisationRebobinage />}
        </>
      );
    }
    render(
      <OptimisationPoseProvider>
        <Inner />
      </OptimisationPoseProvider>,
    );

    // Pré-rempli depuis profil.
    await waitFor(() =>
      expect(screen.getByTestId("store-sens")).toHaveTextContent("7"),
    );
    const sens = screen.getByTestId(
      "sens-enroulement-input",
    ) as HTMLInputElement;
    expect(sens.value).toBe("7");

    // Override : 7 → 2. Le store reflète l'override.
    await userEvent.clear(sens);
    await userEvent.type(sens, "2");
    await waitFor(() =>
      expect(screen.getByTestId("store-sens")).toHaveTextContent("2"),
    );
  });

  // ──────────────────────────────────────────────────────────────────
  // Bug #6 (6.2) — Ø PAR LOT via /api/rebobinage/calculer-multilots
  // ──────────────────────────────────────────────────────────────────

  it("envoie 1 entrée PAR LOT sur /calculer-multilots (matiere_id + nb étiquettes du lot)", async () => {
    setupRebobinage({ briefClient: { diametre_max_bobine_mm: 300 } });

    const multiCall = await waitFor(() => {
      const c = fetchSpy.mock.calls.find((x) =>
        String(x[0]).includes("/api/rebobinage/calculer-multilots"),
      );
      expect(c).toBeTruthy();
      return c!;
    });
    const body = JSON.parse((multiCall[1] as RequestInit).body as string);
    expect(body.lots).toHaveLength(1);
    expect(body.lots[0].matiere_id).toBe(1);
    expect(body.lots[0].nb_etiquettes_total).toBe(12000);
    // Pas de saisie / pas d'override → null (le backend résout depuis la
    // matière + la paroi tenant).
    expect(body.lots[0].epaisseur_saisie_um).toBeNull();
    expect(body.lots[0].paroi_override_mm).toBeNull();
  });

  it("override paroi mandrin : la valeur saisie part dans paroi_override_mm de chaque lot", async () => {
    setupRebobinage({ briefClient: { diametre_max_bobine_mm: 300 } });
    await screen.findByTestId("paroi-override-input");

    await userEvent.type(screen.getByTestId("paroi-override-input"), "4");
    await userEvent.click(screen.getByTestId("rebobinage-recalculer"));

    await waitFor(() => {
      const last = [...fetchSpy.mock.calls]
        .reverse()
        .find((c) =>
          String(c[0]).includes("/api/rebobinage/calculer-multilots"),
        );
      expect(last).toBeTruthy();
      const b = JSON.parse((last![1] as RequestInit).body as string);
      expect(b.lots[0].paroi_override_mm).toBe(4);
    });
  });

  it("affiche un Ø et un nb bobines PAR LOT depuis la réponse multi-lots", async () => {
    installFetchMock(
      buildResultat(),
      buildMultilotsResponse({
        lots: [
          {
            epaisseur_effective_um: 90,
            epaisseur_source: "matiere",
            mandrin_mm: 76,
            paroi_mm: 3,
            diametre_depart_mm: 82,
            diametre_bobine_mm: 305,
            rebobinage: buildResultat({
              bobines: {
                nb_etiq_par_bobine: 1500,
                nb_bobines: 7,
                bobine_partielle: false,
                nb_etiq_derniere_bobine: 1500,
                longueur_totale_m: "900.00",
              },
            }),
          },
        ],
      }),
    );
    setupRebobinage({ briefClient: { diametre_max_bobine_mm: 300 } });

    expect(await screen.findByTestId("lot-diametre-0")).toHaveTextContent(
      "305 mm",
    );
    expect(screen.getByTestId("lot-nb-bobines-0")).toHaveTextContent("7");
  });

  it("badge source épaisseur : 'matière' / 'saisie opérateur' / 'fallback 150 µm'", async () => {
    const cas: Array<{
      source: "matiere" | "saisie" | "fallback";
      attendu: RegExp;
    }> = [
      { source: "matiere", attendu: /matière/i },
      { source: "saisie", attendu: /saisie opérateur/i },
      { source: "fallback", attendu: /fallback 150 µm/i },
    ];
    for (const c of cas) {
      installFetchMock(
        buildResultat(),
        buildMultilotsResponse({
          lots: [
            {
              epaisseur_effective_um: c.source === "fallback" ? 150 : 90,
              epaisseur_source: c.source,
              mandrin_mm: 76,
              paroi_mm: 0,
              diametre_depart_mm: 76,
              diametre_bobine_mm: 300,
              rebobinage: buildResultat(),
            },
          ],
        }),
      );
      const { unmount } = setupRebobinage({
        briefClient: { diametre_max_bobine_mm: 300 },
      });
      const badge = await screen.findByTestId("lot-source-0");
      expect(badge).toHaveTextContent(c.attendu);
      unmount();
    }
  });

  // ──────────────────────────────────────────────────────────────────
  // Bug #6 (6.2d) — recalcul multilots à la saisie override + avant persist
  // ──────────────────────────────────────────────────────────────────

  it("override paroi modifié → multilots recalculé avec paroi_override_mm SANS clic « Recalculer »", async () => {
    setupRebobinage({ briefClient: { diametre_max_bobine_mm: 300 } });
    await screen.findByTestId("paroi-override-input");
    // Calcul initial (override vide) déjà parti.
    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some((c) =>
          String(c[0]).includes("/api/rebobinage/calculer-multilots"),
        ),
      ).toBe(true),
    );

    // On tape l'override SANS cliquer « Recalculer » → recalcul auto (debounce).
    await userEvent.type(screen.getByTestId("paroi-override-input"), "5");

    await waitFor(
      () => {
        const last = [...fetchSpy.mock.calls]
          .reverse()
          .find((c) =>
            String(c[0]).includes("/api/rebobinage/calculer-multilots"),
          );
        const b = JSON.parse((last![1] as RequestInit).body as string);
        expect(b.lots[0].paroi_override_mm).toBe(5);
      },
      { timeout: 2000 },
    );
  });

  it("« Continuer » recalcule le multilots (override paroi) avant de persister + passer au chiffrage", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("paroi-override-input");

    await userEvent.type(screen.getByTestId("paroi-override-input"), "5");
    // Clic immédiat (avant le debounce 400 ms) : le recalcul provient de
    // validerEtContinuer, pas de l'effet debouncé.
    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    await waitFor(() =>
      expect(screen.getByTestId("etape-courante")).toHaveTextContent(
        "chiffrage",
      ),
    );

    const multiCall = [...fetchSpy.mock.calls]
      .reverse()
      .find((c) =>
        String(c[0]).includes("/api/rebobinage/calculer-multilots"),
      );
    expect(multiCall).toBeTruthy();
    const b = JSON.parse((multiCall![1] as RequestInit).body as string);
    expect(b.lots[0].paroi_override_mm).toBe(5);
  });
});
