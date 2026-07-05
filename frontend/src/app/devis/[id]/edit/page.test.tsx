import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DevisDetail } from "@/lib/api";

// Non-régression du fix `fix(ui): edit devis multi-lots redirige vers
// /optimisation?devis_id=X`. Vérifie que :
//   - devis multi-lots → router.replace appelé avec /optimisation?devis_id
//   - devis mono-lot   → DevisCalculForm monté, pas de redirect

const useParamsMock = vi.fn();
const routerReplaceMock = vi.fn();
const routerPushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => useParamsMock(),
  useRouter: () => ({
    replace: routerReplaceMock,
    push: routerPushMock,
  }),
}));

const getDevisDetailMock = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getDevisDetail: (...args: Parameters<typeof actual.getDevisDetail>) =>
      getDevisDetailMock(...args),
  };
});

// Stubs des composants lourds — leur intégration n'est pas testée ici.
vi.mock("@/components/DevisCalculForm", () => ({
  DevisCalculForm: () => <div data-testid="devis-calcul-form-stub" />,
}));
vi.mock("@/components/DevisResult", () => ({
  DevisResult: () => <div data-testid="devis-result-stub" />,
}));
vi.mock("@/components/DevisSaveBar", () => ({
  DevisSaveBar: () => <div data-testid="devis-save-bar-stub" />,
}));

import EditDevisPage from "./page";

function buildDevis(overrides: Partial<DevisDetail> = {}): DevisDetail {
  return {
    id: 42,
    numero: "DEV-2026-0042",
    date_creation: "2026-05-24T00:00:00",
    date_modification: "2026-05-24T00:00:00",
    statut: "brouillon",
    client_id: null,
    client_nom: null,
    machine_id: 1,
    machine_nom: "MA-1",
    payload_input: {},
    payload_output: {},
    mode_calcul: "manuel",
    cylindre_choisi_z: null,
    cylindre_choisi_nb_etiq: null,
    format_h_mm: "80",
    format_l_mm: "100",
    ht_total_eur: "1000.00",
    ...overrides,
  };
}

describe("EditDevisPage — fix multi-lots redirect", () => {
  beforeEach(() => {
    useParamsMock.mockReset();
    routerReplaceMock.mockReset();
    routerPushMock.mockReset();
    getDevisDetailMock.mockReset();
    useParamsMock.mockReturnValue({ id: "42" });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("devis multi-lots : router.replace vers /optimisation?devis_id=X, DevisCalculForm pas monté", async () => {
    getDevisDetailMock.mockResolvedValueOnce(
      buildDevis({
        id: 42,
        // Critère #1 du fix : lots_production non-vide.
        lots_production: [
          {
            id: 1,
            ordre: 1,
            cylindre_id: 10,
            machine_id: 1,
            nb_poses_dev: 2,
            nb_poses_laize: 5,
            sens_enroulement: 1,
            quantite: 5000,
            matiere_id: 1,
            intervalle_dev_reel_mm: null,
            intervalle_laize_reel_mm: null,
            largeur_plaque_mm: null,
            score_optim: null,
            cout_lot_ht_eur: null,
            created_at: "2026-05-24T00:00:00",
            updated_at: "2026-05-24T00:00:00",
            machine_nom: "MA-1",
            cylindre_nb_dents: 104,
            cylindre_developpe_mm: "330.20",
            matiere_libelle: "PP blanc",
            sens_enroulement_libelle: null,
            rotation_vue_a_deg: null,
            rotation_vue_c_deg: null,
            payload_visuel: null,
            changement_outil_cliche: false,
          },
        ],
      }),
    );

    render(<EditDevisPage />);

    await waitFor(() =>
      expect(routerReplaceMock).toHaveBeenCalledWith(
        "/optimisation?devis_id=42",
      ),
    );
    // Frame intermédiaire : on rend "Redirection vers l'optimisation…",
    // pas DevisCalculForm.
    expect(screen.queryByTestId("devis-calcul-form-stub")).toBeNull();
    expect(
      screen.getByText(/Redirection vers l'optimisation/i),
    ).toBeInTheDocument();
  });

  it("devis multi-lots via payload_output.mode='multi-lots' (sans lots_production) : redirect aussi", async () => {
    // Critère #2 du fix : payload_output.mode === "multi-lots" suffit même
    // si lots_production est vide (devis legacy ou cas dégradé).
    getDevisDetailMock.mockResolvedValueOnce(
      buildDevis({ id: 7, payload_output: { mode: "multi-lots" } }),
    );

    render(<EditDevisPage />);

    await waitFor(() =>
      expect(routerReplaceMock).toHaveBeenCalledWith(
        "/optimisation?devis_id=7",
      ),
    );
  });

  it("devis mono-lot : DevisCalculForm monté, pas de redirect", async () => {
    getDevisDetailMock.mockResolvedValueOnce(
      buildDevis({
        // mono-lot : ni lots_production rempli, ni payload_output.mode multi-lots.
        lots_production: [],
        payload_output: { mode: "mono-lot", autre_champ: "valeur" },
      }),
    );

    render(<EditDevisPage />);

    await waitFor(() =>
      expect(
        screen.getByTestId("devis-calcul-form-stub"),
      ).toBeInTheDocument(),
    );
    expect(routerReplaceMock).not.toHaveBeenCalled();
    expect(
      screen.queryByText(/Redirection vers l'optimisation/i),
    ).toBeNull();
  });
});
