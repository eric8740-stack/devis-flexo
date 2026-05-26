import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import type {
  OptimisationConfigOut,
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

let fetchSpy: ReturnType<typeof vi.fn>;

function installFetchMock(defaultResult: RebobinageResultat = buildResultat()) {
  fetchSpy = vi.fn(async () => ({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => defaultResult,
  }));
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
    } = useOptimisationPose();
    useEffect(() => {
      if (opts.briefClient) setBriefClient(opts.briefClient);
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
});
