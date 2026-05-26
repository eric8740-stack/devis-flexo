import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import { OptimisationRebobinage } from "./OptimisationRebobinage";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./OptimisationPoseStore";

// Sprint 16 Lot D — non-régression du composant OptimisationRebobinage.
// Couvre les deux invariants critiques du brief :
//   1. Pré-remplissage des champs bobine depuis le brief client (store).
//   2. Forçage commercial du mode → motif obligatoire (validation
//      bloquante avant passage à l'étape chiffrage).

/**
 * Wrapper de test : configure le store puis bascule sur l'étape
 * "rebobinage" avant de monter OptimisationRebobinage. Permet de simuler
 * le parcours réel (saisie → candidats → detail → rebobinage) sans avoir
 * à lancer les étapes amont.
 */
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
    } = useOptimisationPose();
    useEffect(() => {
      // 1. Pose les valeurs du brief client (alimentent le pré-remplissage).
      if (opts.briefClient) {
        setBriefClient(opts.briefClient);
      }
      // 2. Pose mandrin + quantité totale comme le ferait l'étape "saisie"
      //    avant de basculer en "candidats". On passe par goCandidats puis
      //    goRebobinage pour aligner avec le vrai parcours du store.
      goCandidats([], 10000, 100, 80, opts.mandrinInitial ?? 76);
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
 * Spy sur l'étape courante depuis le store, monté à côté de
 * OptimisationRebobinage pour observer la navigation après clic
 * "Continuer vers chiffrage".
 */
function setupRebobinageAvecSpyEtape() {
  function EtapeSpy() {
    const { etape } = useOptimisationPose();
    return <div data-testid="etape-courante">{etape}</div>;
  }
  function Inner() {
    const { etape, goRebobinage, goCandidats } = useOptimisationPose();
    useEffect(() => {
      goCandidats([], 10000, 100, 80, 76);
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

describe("OptimisationRebobinage — Sprint 16 Lot D", () => {
  beforeEach(() => {
    window.localStorage.clear();
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

    // Attendre que les inputs apparaissent (effet useEffect du wrapper
    // a basculé l'étape sur "rebobinage").
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
  });

  it("pas de brief client → inputs vides + mandrin par défaut", async () => {
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
    // 76 mm = default workflow (cf store).
    expect(mandrin.value).toBe("76");
  });

  it("forçage mode sans motif : erreur affichée, étape reste 'rebobinage'", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("forcer-mode-checkbox");

    // L'opérateur active le forçage mais ne saisit pas de motif.
    await userEvent.click(screen.getByTestId("forcer-mode-checkbox"));
    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    // Erreur visible, et l'étape n'a PAS changé : on est toujours sur
    // "rebobinage" (le passage à "chiffrage" est bloqué).
    expect(screen.getByTestId("motif-erreur")).toHaveTextContent(
      /Motif obligatoire/i,
    );
    expect(screen.getByTestId("etape-courante")).toHaveTextContent(
      "rebobinage",
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

  it("forçage mode + motif valide : passage à l'étape 'chiffrage', pas d'erreur", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("forcer-mode-checkbox");

    await userEvent.click(screen.getByTestId("forcer-mode-checkbox"));
    await userEvent.type(
      screen.getByTestId("motif-force-textarea"),
      "Contrainte client export Asie urgence",
    );
    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    // Étape mise à jour → on n'est plus sur "rebobinage" donc le composant
    // est démonté côté spy ; on assert juste la nouvelle étape.
    await waitFor(() =>
      expect(screen.getByTestId("etape-courante")).toHaveTextContent(
        "chiffrage",
      ),
    );
    expect(screen.queryByTestId("motif-erreur")).toBeNull();
  });

  it("pas de forçage : clic Continuer passe directement à 'chiffrage'", async () => {
    setupRebobinageAvecSpyEtape();
    await screen.findByTestId("rebobinage-continuer");

    await userEvent.click(screen.getByTestId("rebobinage-continuer"));

    await waitFor(() =>
      expect(screen.getByTestId("etape-courante")).toHaveTextContent(
        "chiffrage",
      ),
    );
  });
});
