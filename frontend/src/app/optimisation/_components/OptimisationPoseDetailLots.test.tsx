import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect } from "react";

import type { MatiereOut, OptimisationConfigOut } from "@/lib/api";

import { OptimisationPoseDetailLots } from "./OptimisationPoseDetailLots";
import {
  OptimisationPoseProvider,
  useOptimisationPose,
} from "./OptimisationPoseStore";

// SchemaImplantation (SACRED, SVG complexe) hors périmètre de ce test :
// on le réduit à un placeholder pour isoler la logique « épaisseur par lot ».
vi.mock("@/components/SchemaImplantation", () => ({
  SchemaImplantation: () => <div data-testid="schema-implantation" />,
}));

// Bug #6 (6.2) — l'étape Matière propose une saisie opérateur d'épaisseur
// quand la matière du lot n'a pas d'`epaisseur_microns` au catalogue ; sinon
// elle affiche l'épaisseur catalogue en lecture seule.

function buildMatieres(): MatiereOut[] {
  const base = {
    code: "X",
    categorie: null,
    sous_type: null,
    grammage_gm2: null,
    est_transparent: false,
    opacite_pct: null,
    certifications_sanitaires: null,
    certifications_env: null,
    adhesifs_compatibles: null,
    actif: true,
  };
  return [
    // id=1 : SANS épaisseur catalogue → saisie opérateur attendue.
    { ...base, id: 1, libelle: "Vélin caractérisé grammage", epaisseur_microns: null },
    // id=2 : AVEC épaisseur catalogue → lecture seule.
    { ...base, id: 2, libelle: "PET blanc 50µ", epaisseur_microns: 50 },
  ];
}

let fetchSpy: ReturnType<typeof vi.fn>;

function installFetchMock(matieres: MatiereOut[] = buildMatieres()) {
  fetchSpy = vi.fn(async () => ({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => matieres,
  }));
  global.fetch = fetchSpy as unknown as typeof fetch;
}

function fakeCandidat(
  overrides: Partial<OptimisationConfigOut> = {},
): OptimisationConfigOut {
  // Champs minimaux lus par DetailLots + buildIdCandidat ; le reste n'est
  // pas rendu (SchemaImplantation mocké).
  return {
    cylindre_id: 1,
    machine_id: 1,
    nb_poses_dev: 2,
    nb_poses_laize: 5,
    nb_poses_total: 10,
    nb_dents_cylindre: 104,
    z_cylindre_mm: 330.2,
    noms_machines_compatibles: ["MA-1"],
    score: 100,
    sens_enroulement: "SE1",
    ...overrides,
  } as unknown as OptimisationConfigOut;
}

function setupDetail(candidat: OptimisationConfigOut = fakeCandidat()) {
  function EpaisseurSpy() {
    const { selection } = useOptimisationPose();
    return (
      <div data-testid="store-epaisseur-0">
        {selection[0]?.epaisseur_saisie_um ?? "null"}
      </div>
    );
  }
  function Inner() {
    const { goCandidats, toggleSelection, setQuantiteLot } =
      useOptimisationPose();
    useEffect(() => {
      goCandidats([candidat], 12000, 100, 80, 76);
      toggleSelection(candidat);
      const id = `${candidat.cylindre_id}-${candidat.machine_id}-${candidat.nb_poses_dev}x${candidat.nb_poses_laize}-${candidat.sens_enroulement}`;
      setQuantiteLot(id, 12000);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    return (
      <>
        <EpaisseurSpy />
        <OptimisationPoseDetailLots />
      </>
    );
  }
  return render(
    <OptimisationPoseProvider>
      <Inner />
    </OptimisationPoseProvider>,
  );
}

describe("OptimisationPoseDetailLots — épaisseur par lot (bug #6)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    installFetchMock();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("matière SANS épaisseur catalogue → champ de saisie opérateur, propagé au store", async () => {
    setupDetail();
    // Attendre le chargement des matières.
    const select = (await screen.findByRole("combobox")) as HTMLSelectElement;

    // Tant qu'aucune matière n'est choisie : pas de champ épaisseur.
    expect(screen.queryByTestId("epaisseur-saisie-0")).toBeNull();
    expect(screen.queryByTestId("epaisseur-catalogue-0")).toBeNull();

    // Sélection de la matière SANS épaisseur (id=1).
    await userEvent.selectOptions(select, "1");

    const input = (await screen.findByTestId(
      "epaisseur-saisie-0",
    )) as HTMLInputElement;
    expect(screen.queryByTestId("epaisseur-catalogue-0")).toBeNull();

    // Saisie → round-trip via le store (input contrôlé par le store).
    await userEvent.type(input, "90");
    await waitFor(() => expect(input.value).toBe("90"));
    expect(screen.getByTestId("store-epaisseur-0")).toHaveTextContent("90");
  });

  it("matière AVEC épaisseur catalogue → lecture seule, pas de champ de saisie", async () => {
    setupDetail();
    const select = (await screen.findByRole("combobox")) as HTMLSelectElement;

    // Sélection de la matière AVEC épaisseur (id=2, 50 µm).
    await userEvent.selectOptions(select, "2");

    const catalogue = await screen.findByTestId("epaisseur-catalogue-0");
    expect(catalogue).toHaveTextContent("50 µm");
    expect(screen.queryByTestId("epaisseur-saisie-0")).toBeNull();
  });
});

// L1 — décompo laize (lecture seule) depuis le contrat `geometrie_laize`.
describe("OptimisationPoseDetailLots — décompo laize (L1)", () => {
  beforeEach(() => {
    window.localStorage.clear();
    installFetchMock();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("affiche la décompo laize quand geometrie_laize est présent", async () => {
    setupDetail(
      fakeCandidat({
        geometrie_laize: {
          laize_plaque_mm: 200,
          bord_lateral_mm: 10,
          laize_papier_mm: 220,
          intervalle_laize_mm: 2,
        },
      }),
    );
    const decompo = await screen.findByTestId("decompo-laize-0");
    expect(decompo).toHaveTextContent("200 mm"); // imprimé (laize plaque)
    expect(decompo).toHaveTextContent("10 mm"); // 2 × bord
    expect(decompo).toHaveTextContent("220 mm"); // laize papier réelle
    // Garde-fou : aucun affichage d'impact prix (L1 informatif).
    expect(decompo).not.toHaveTextContent("€");
  });

  it("pas de décompo si geometrie_laize absent (devis legacy) — aucun crash", async () => {
    setupDetail(fakeCandidat()); // pas de geometrie_laize
    // Le composant se monte (le sélecteur matière apparaît) sans la décompo.
    await screen.findByRole("combobox");
    expect(screen.queryByTestId("decompo-laize-0")).toBeNull();
  });

  it("bord forcé : surface l'écho forcage_bord_lateral + motif", async () => {
    setupDetail(
      fakeCandidat({
        geometrie_laize: {
          laize_plaque_mm: 200,
          bord_lateral_mm: 15,
          laize_papier_mm: 230,
          intervalle_laize_mm: 2,
        },
        forcage_bord_lateral: true,
        motif_bord_lateral: "Contrainte client export",
      }),
    );
    const force = await screen.findByTestId("bord-force-0");
    expect(force).toHaveTextContent(/Bord latéral forcé/);
    expect(force).toHaveTextContent("Contrainte client export");
  });

  it("bord au défaut (forcage false) : pas d'écho forcé", async () => {
    setupDetail(
      fakeCandidat({
        geometrie_laize: {
          laize_plaque_mm: 200,
          bord_lateral_mm: 10,
          laize_papier_mm: 220,
          intervalle_laize_mm: 2,
        },
        forcage_bord_lateral: false,
      }),
    );
    await screen.findByTestId("decompo-laize-0");
    expect(screen.queryByTestId("bord-force-0")).toBeNull();
  });

  // Lot back A — mode « format sans outil » : déchet latéral + nb filles.
  it("mode sans outil : déchet latéral (stock − utile) + nb filles affichés", async () => {
    setupDetail(
      fakeCandidat({
        geometrie_laize: {
          laize_plaque_mm: 300,
          bord_lateral_mm: 0,
          laize_papier_mm: 320,
          intervalle_laize_mm: 0,
          laize_stock_mm: 330,
          laize_utile_mm: 320,
          dechet_lateral_mm: 10,
          nb_filles: 4,
        },
      }),
    );
    const d = await screen.findByTestId("dechet-lateral-0");
    expect(d).toHaveTextContent("330 mm"); // stock
    expect(d).toHaveTextContent("320 mm"); // utile
    expect(d).toHaveTextContent("10 mm"); // déchet
    expect(d).toHaveTextContent(/4 bobine\(s\) fille\(s\)/);
  });

  it("mode avec outil (dechet null) : pas de ligne déchet latéral", async () => {
    setupDetail(
      fakeCandidat({
        geometrie_laize: {
          laize_plaque_mm: 200,
          bord_lateral_mm: 10,
          laize_papier_mm: 220,
          intervalle_laize_mm: 2,
        },
      }),
    );
    await screen.findByTestId("decompo-laize-0");
    expect(screen.queryByTestId("dechet-lateral-0")).toBeNull();
  });
});
