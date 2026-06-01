import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PorteClichesOnglet } from "./PorteClichesOnglet";

// Non-régression du fix `fix(ui): mon-parc cylindres désactivés visibles
// + filtre Toutes porte-clichés`. Vérifie que sélectionner "Toutes" dans
// le dropdown machine déclenche bien un rafraîchissement de la liste —
// avant le fix, le `useEffect` avait `if (machineFilter !== null)
// rafraichir()` qui figeait la liste sur le dernier filtre actif.

interface MockResponse {
  urlPart: string;
  body: unknown;
}

function installFetchMock(responses: MockResponse[]) {
  // Ordre : on retourne le PREMIER match → ranger les URL les plus
  // spécifiques (avec &machine_id=…) en premier, les génériques après.
  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : (input as Request).url;
    const match = responses.find((r) => url.includes(r.urlPart));
    if (!match) {
      throw new Error(`No mock for ${url}`);
    }
    return {
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => match.body,
    } as Response;
  }) as typeof fetch;
}

function buildPc(overrides: Partial<{
  id: number;
  machine_id: number;
  machine_nom: string;
  machine_nb_couleurs: number | null;
  cylindre_id: number;
  cylindre_nb_dents: number;
  cylindre_developpe_mm: string;
  quantite: number;
  notes: string | null;
  actif: boolean;
}>) {
  return {
    id: 1,
    machine_id: 1,
    machine_nom: "MA-1",
    machine_nb_couleurs: 8,
    cylindre_id: 10,
    cylindre_nb_dents: 100,
    cylindre_developpe_mm: "317.50",
    quantite: 8,
    notes: null,
    actif: true,
    created_at: "2026-05-01T00:00:00",
    updated_at: "2026-05-01T00:00:00",
    ...overrides,
  };
}

const MACHINE_1 = {
  id: 1,
  nom: "MA-1",
  largeur_max_mm: 330,
  laize_max_mm: 250,
  vitesse_max_m_min: 100,
  vitesse_moyenne_m_h: 5000,
  duree_calage_h: 0.5,
  nb_groupes_couleurs: 8,
  cout_horaire_eur: 100,
  laize_utile_mm: 250,
  nb_postes_decoupe: 1,
  vitesse_pratique_m_min: 100,
  options: [],
  actif: true,
  commentaire: null,
  date_creation: "2026-01-01T00:00:00",
  date_maj: "2026-01-01T00:00:00",
};
const MACHINE_2 = { ...MACHINE_1, id: 2, nom: "MA-2" };

describe("PorteClichesOnglet — fix filtre Toutes", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sélection 'Toutes' (machineFilter=null) déclenche rafraîchir → liste mise à jour", async () => {
    installFetchMock([
      // Initial : filtre auto-sélectionné sur machine 1 → renvoie un PC
      // associé à cyl 100 dents.
      {
        urlPart: "porte-cliches?actif=true&machine_id=1",
        body: [buildPc({ id: 1, cylindre_nb_dents: 100 })],
      },
      {
        urlPart: "porte-cliches?actif=false&machine_id=1",
        body: [],
      },
      // Après clic « Toutes » (pas de machine_id) → renvoie PC machine 1 +
      // PC machine 2 (cyl 120 dents).
      {
        urlPart: "porte-cliches?actif=true",
        body: [
          buildPc({ id: 1, cylindre_nb_dents: 100, machine_id: 1 }),
          buildPc({
            id: 2,
            cylindre_nb_dents: 120,
            cylindre_developpe_mm: "381.00",
            machine_id: 2,
            machine_nom: "MA-2",
          }),
        ],
      },
      {
        urlPart: "porte-cliches?actif=false",
        body: [],
      },
      // Référentiels (chargés une seule fois en init).
      { urlPart: "/api/machines", body: [MACHINE_1, MACHINE_2] },
      {
        urlPart: "/api/cylindres?actif=true",
        body: [
          {
            id: 10,
            nb_dents: 100,
            developpe_mm: "317.50",
            actif: true,
            notes: null,
            date_creation: "2026-01-01T00:00:00",
          },
        ],
      },
    ]);

    render(<PorteClichesOnglet />);

    // Étape 1 : filtre initial sur machine 1 → seul le PC cyl 317.50 mm
    // est visible. Le PC machine 2 (cyl 381.00 mm) n'apparaît pas encore.
    // On cible le développé (Z = X mm) plutôt que le nb dents car ce
    // dernier apparaît plusieurs fois par card (titre + sous-texte).
    await waitFor(() =>
      expect(screen.getByText(/Z = 317.50 mm/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/Z = 381.00 mm/)).toBeNull();

    // Étape 2 : utilisateur sélectionne « Toutes » dans le dropdown
    // machine — la value est "" (option Toutes).
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    await userEvent.selectOptions(select, "");

    // Étape 3 : la liste se met à jour → le PC cyl 381.00 mm (machine 2)
    // apparaît maintenant. C'est la régression que le fix corrige : avant,
    // `if (machineFilter !== null) rafraichir()` figeait la liste.
    await waitFor(() =>
      expect(screen.getByText(/Z = 381.00 mm/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Z = 317.50 mm/)).toBeInTheDocument();
  });
});
