import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/types/auth";

// Sprint 15 Lot C — tests RTL de la page détail Contrôle BAT.
// Mocke useAuth, useParams (next/navigation) et les fonctions API du module
// isolé controleBat.

const useAuthMock = vi.fn();
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

const useParamsMock = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => useParamsMock(),
}));

const getContextMock = vi.fn();
const createControleMock = vi.fn();
vi.mock("@/lib/api/controleBat", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/api/controleBat")>();
  return {
    ...actual,
    getControleBatContext: (
      ...args: Parameters<typeof actual.getControleBatContext>
    ) => getContextMock(...args),
    createControleBat: (
      ...args: Parameters<typeof actual.createControleBat>
    ) => createControleMock(...args),
  };
});

import AtelierControleBatDetailPage from "./page";

function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: "ops@acme.test",
    nom_contact: "Op Atelier",
    entreprise_id: 1,
    nom_entreprise: "ACME",
    is_admin: false,
    is_active: true,
    date_creation: "2026-01-01T00:00:00",
    date_derniere_connexion: null,
    has_flexocheck: true,
    ...overrides,
  };
}

function buildContext(overrides: Partial<{
  devis_id: number;
  devis_numero: string;
  client_nom: string | null;
  designation: string | null;
  machine_nom: string;
  bat_url: string;
  bat_mime_type: string;
}> = {}) {
  // bat_url = "about:blank" : happy-dom n'essaie pas de fetcher l'URL pour
  // l'iframe PDF (sinon pollution `getaddrinfo ENOTFOUND` ou DOMException
  // sur les fixtures). Pour vérifier qu'on rend bien la bonne URL côté
  // code prod, on a déjà les tests du client API (getControleBatContext)
  // qui prouvent que `bat_url` est conservé dans la réponse.
  return {
    devis_id: 7,
    devis_numero: "DEV-2026-0007",
    client_nom: "ACME",
    designation: "Étiquette 50×80",
    machine_nom: "Mark Andy P5",
    bat_url: "about:blank",
    bat_mime_type: "application/pdf",
    ...overrides,
  };
}

describe("AtelierControleBatDetailPage — Lot C", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
    useParamsMock.mockReset();
    getContextMock.mockReset();
    createControleMock.mockReset();
    useParamsMock.mockReturnValue({ id: "7" });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("user sans has_flexocheck : message d'accès, pas d'appel getContext", () => {
    useAuthMock.mockReturnValue({
      user: buildUser({ has_flexocheck: false }),
    });

    render(<AtelierControleBatDetailPage />);

    expect(
      screen.getByText(/Module FlexoCheck non activé/i),
    ).toBeInTheDocument();
    expect(getContextMock).not.toHaveBeenCalled();
  });

  it("404 contexte : bandeau alert affiché, pas de sections BAT/protocole", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockRejectedValueOnce(
      new Error("GET /api/.../contexte/7 → 404 Devis introuvable"),
    );

    render(<AtelierControleBatDetailPage />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/introuvable/i),
    );
    expect(screen.queryByTestId("protocole-photo")).toBeNull();
    expect(screen.queryByTestId("bat-pdf")).toBeNull();
  });

  it("BAT PDF : iframe rendu + encart protocole visible avec 4 consignes", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());

    render(<AtelierControleBatDetailPage />);

    await waitFor(() =>
      expect(screen.getByTestId("bat-pdf")).toBeInTheDocument(),
    );

    const protocole = screen.getByTestId("protocole-photo");
    expect(protocole).toHaveTextContent(/Face à la sortie presse/i);
    expect(protocole).toHaveTextContent(/1 m/);
    expect(protocole).toHaveTextContent(/perpendiculaire/i);
    expect(protocole).toHaveTextContent(/fond vers l'opérateur/i);
    expect(protocole).toHaveTextContent(/pas de flash/i);
  });

  it("BAT image : balise img rendue avec capture environment sur l'input photo", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(
      buildContext({
        bat_url: "data:image/png;base64,iVBORw0KGgo=",
        bat_mime_type: "image/png",
      }),
    );

    render(<AtelierControleBatDetailPage />);

    await waitFor(() =>
      expect(screen.getByTestId("bat-image")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("bat-pdf")).toBeNull();

    const photoInput = screen.getByTestId("photo-input") as HTMLInputElement;
    expect(photoInput.getAttribute("capture")).toBe("environment");
    expect(photoInput.getAttribute("accept")).toBe("image/*");
  });

  it("sélection non-image : erreur validation, bouton Analyser absent", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());

    render(<AtelierControleBatDetailPage />);
    await screen.findByTestId("bat-pdf");

    const photoInput = screen.getByTestId("photo-input") as HTMLInputElement;
    const wrongFile = new File(["x"], "notes.pdf", { type: "application/pdf" });
    await userEvent.upload(photoInput, wrongFile, { applyAccept: false });

    expect(screen.getByRole("alert")).toHaveTextContent(/Format non supporté/i);
    expect(
      screen.queryByRole("button", { name: /Analyser la conformité/i }),
    ).toBeNull();
  });

  it("submit happy path : animation 'Analyse en cours', appel API, placeholder résultat", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());

    // createControleBat ne résout qu'après que le test ait observé l'animation.
    let resolveCreate: (v: unknown) => void = () => {};
    createControleMock.mockReturnValueOnce(
      new Promise((res) => {
        resolveCreate = res;
      }),
    );

    render(<AtelierControleBatDetailPage />);
    await screen.findByTestId("bat-pdf");

    const photoInput = screen.getByTestId("photo-input") as HTMLInputElement;
    const photo = new File(["JPEG"], "tirage.jpg", { type: "image/jpeg" });
    await userEvent.upload(photoInput, photo);

    expect(screen.getByTestId("photo-preview")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /Analyser la conformité/i }),
    );

    // Animation visible pendant le call.
    expect(screen.getByTestId("analyzing-banner")).toBeInTheDocument();
    expect(screen.getByTestId("analyzing-banner")).toHaveTextContent(
      /5 à 10 secondes/i,
    );
    expect(createControleMock).toHaveBeenCalledWith(7, photo);

    // Résolution du fetch → placeholder résultat affiché, animation disparue.
    resolveCreate({
      controle_id: 101,
      devis_id: 7,
      tentative: 1,
      score_conformite: 87.5,
      decision_recommandee: "valider",
    });
    await waitFor(() =>
      expect(screen.getByTestId("result-placeholder")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("analyzing-banner")).toBeNull();
    expect(screen.getByTestId("result-placeholder")).toHaveTextContent(
      /contrôle #101/i,
    );
  });

  it("erreur analyse : bandeau alert avec detail, animation disparue, pas de result-placeholder", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());
    createControleMock.mockRejectedValueOnce(
      new Error("POST → 503 Service IA temporairement indisponible"),
    );

    render(<AtelierControleBatDetailPage />);
    await screen.findByTestId("bat-pdf");

    const photoInput = screen.getByTestId("photo-input") as HTMLInputElement;
    await userEvent.upload(
      photoInput,
      new File(["JPEG"], "t.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Analyser la conformité/i }),
    );

    await waitFor(() =>
      expect(
        screen.getByText(/Analyse impossible/i),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("analyzing-banner")).toBeNull();
    expect(screen.queryByTestId("result-placeholder")).toBeNull();
  });
});
