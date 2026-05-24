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
const relancerTirageMock = vi.fn();
const decideControleMock = vi.fn();
const fetchBlobMock = vi.fn();
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
    relancerTirage: (
      ...args: Parameters<typeof actual.relancerTirage>
    ) => relancerTirageMock(...args),
    decideControleBat: (
      ...args: Parameters<typeof actual.decideControleBat>
    ) => decideControleMock(...args),
    fetchControleBatBlob: (
      ...args: Parameters<typeof actual.fetchControleBatBlob>
    ) => fetchBlobMock(...args),
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
  designation: string;
  machine_nom: string;
  bat_url: string | null;
  bat_mime_type: string | null;
}> = {}) {
  // bat_url côté backend = `/api/flexocheck/blobs/{key}` (endpoint
  // authentifié). Le composant BatBlobAuthenticated passe par
  // fetchControleBatBlob (mocké via vi.mock plus haut) qui renvoie un
  // objectURL local → aucune requête réseau effective en test.
  return {
    devis_id: 7,
    devis_numero: "DEV-2026-0007",
    client_nom: "ACME",
    designation: "DEV-2026-0007",
    machine_nom: "Mark Andy P5",
    bat_url: "/api/flexocheck/blobs/abc.pdf",
    bat_mime_type: "application/pdf",
    ...overrides,
  };
}

function buildAnalyseResult(
  overrides: Partial<{
    controle_id: number;
    devis_id: number;
    tentative: number;
    score_conformite: string | null;
    decision_recommandee: string | null;
    niveau_confiance: string | null;
    limites_analyse: string[];
    ecarts: unknown[];
    elements_conformes: string[];
    elements_manquants: string[];
    sens_enroulement_detecte: string | null;
    sens_enroulement_demande: string | null;
    alerte_sens_enroulement: unknown | null;
    alerte_chef_atelier: boolean | null;
  }> = {},
) {
  // Aligné sur ControleBatAnalyseResponse : listes obligatoires (vides
  // au besoin), score Decimal sérialisé string.
  return {
    controle_id: 100,
    devis_id: 7,
    tentative: 1,
    score_conformite: "80.00",
    decision_recommandee: "valider",
    niveau_confiance: "haut",
    limites_analyse: [],
    ecarts: [],
    elements_conformes: [],
    elements_manquants: [],
    sens_enroulement_detecte: null,
    sens_enroulement_demande: null,
    alerte_sens_enroulement: null,
    alerte_chef_atelier: null,
    ...overrides,
  };
}

describe("AtelierControleBatDetailPage — Lot C", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
    useParamsMock.mockReset();
    getContextMock.mockReset();
    createControleMock.mockReset();
    relancerTirageMock.mockReset();
    decideControleMock.mockReset();
    fetchBlobMock.mockReset();
    // BatBlobAuthenticated fait fetch authentifié dès qu'on lui donne une
    // bat_url non-null. On stub `about:blank` plutôt qu'un faux objectURL
    // (`blob:xxx`) : happy-dom tente de fetcher la src de l'iframe pour de
    // vrai, le scheme `blob:` n'est pas supporté et pollue la sortie de
    // tests avec des DOMException. `about:blank` est un no-op silencieux.
    fetchBlobMock.mockResolvedValue("about:blank");
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
        bat_url: "/api/flexocheck/blobs/img.png",
        bat_mime_type: "image/png",
      }),
    );

    render(<AtelierControleBatDetailPage />);

    // BatBlobAuthenticated fait fetch + objectURL, le testid bat-image
    // n'est rendu qu'une fois le blob disponible.
    await waitFor(() =>
      expect(screen.getByTestId("bat-image")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("bat-pdf")).toBeNull();
    expect(fetchBlobMock).toHaveBeenCalledWith("/api/flexocheck/blobs/img.png");

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

  it("submit happy path : animation 'Analyse en cours', appel API, bloc résultat", async () => {
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

    // Résolution du fetch → bloc résultat affiché, animation disparue.
    resolveCreate(
      buildAnalyseResult({ controle_id: 101, tentative: 1 }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("resultat-controle")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("analyzing-banner")).toBeNull();
    expect(screen.getByTestId("resultat-controle")).toHaveTextContent(
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
    expect(screen.queryByTestId("resultat-controle")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // Lot E — workflow re-tirage + décision opérateur
  // -------------------------------------------------------------------------

  it("après 1ère analyse : timeline #1, ResultatControle, boutons Valider+Ajuster, capture initiale masquée", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());
    createControleMock.mockResolvedValueOnce(
      buildAnalyseResult({
        controle_id: 100,
        tentative: 1,
        score_conformite: "72.00",
        decision_recommandee: "ajuster_avant_demarrage",
      }),
    );

    render(<AtelierControleBatDetailPage />);
    await screen.findByTestId("bat-pdf");
    await userEvent.upload(
      screen.getByTestId("photo-input"),
      new File(["JPEG"], "t1.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Analyser la conformité/i }),
    );

    await waitFor(() =>
      expect(screen.getByTestId("resultat-controle")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("tentatives-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("tentative-chip-1")).toHaveTextContent("#1");
    expect(screen.getByTestId("decision-actions")).toBeInTheDocument();
    // CaptureSection initiale (gros bouton "📷 Prendre photo 1er tirage")
    // doit avoir disparu : photo a été reset après l'analyse.
    expect(
      screen.queryByRole("button", { name: /Prendre photo 1er tirage/i }),
    ).toBeNull();
  });

  it("Ajuster + nouvelle photo + analyser : relancerTirage appelé avec last controle_id, timeline #1+#2", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());
    createControleMock.mockResolvedValueOnce(
      buildAnalyseResult({
        controle_id: 100,
        tentative: 1,
        score_conformite: "60.00",
        decision_recommandee: "ajuster_avant_demarrage",
      }),
    );
    relancerTirageMock.mockResolvedValueOnce(
      buildAnalyseResult({
        // Backend crée un ControleBat distinct par tentative (chaîné via
        // controle_bat_precedent_id), donc nouveau controle_id pour la
        // tentative 2.
        controle_id: 101,
        tentative: 2,
        score_conformite: "88.00",
        decision_recommandee: "valider",
      }),
    );

    render(<AtelierControleBatDetailPage />);
    await screen.findByTestId("bat-pdf");

    // 1ère analyse.
    await userEvent.upload(
      screen.getByTestId("photo-input"),
      new File(["JPEG1"], "t1.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Analyser la conformité/i }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("tentative-chip-1")).toBeInTheDocument(),
    );

    // Ajuster : click déclenche fileInputRef.click() (impossible à
    // observer en happy-dom) puis reset des états → on re-uploade
    // directement sur l'input file pour simuler la sélection caméra.
    await userEvent.click(
      screen.getByRole("button", { name: /Ajuster et recommencer/i }),
    );
    // Après reset, l'input est toujours rendu (sr-only) — on peut re-uploader.
    await userEvent.upload(
      screen.getByTestId("photo-input"),
      new File(["JPEG2"], "t2.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Lancer un nouveau tirage/i }),
    );

    await waitFor(() =>
      expect(relancerTirageMock).toHaveBeenCalledTimes(1),
    );
    // Le retirage est attaché au controle_id de la 1ère analyse.
    expect(relancerTirageMock).toHaveBeenCalledWith(100, expect.any(File));
    expect(createControleMock).toHaveBeenCalledTimes(1);
    // Timeline mise à jour.
    await waitFor(() =>
      expect(screen.getByTestId("tentative-chip-2")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("tentative-chip-1")).toBeInTheDocument();
    expect(screen.getByTestId("resultat-controle")).toHaveTextContent(
      /tentative 2/i,
    );
  });

  it("Valider la production → dialog ouvre, soumission → bloc décision + actions masquées", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());
    createControleMock.mockResolvedValueOnce(
      buildAnalyseResult({
        controle_id: 100,
        tentative: 1,
        score_conformite: "92.00",
        decision_recommandee: "valider",
      }),
    );
    decideControleMock.mockResolvedValueOnce({
      id: 100,
      entreprise_id: 1,
      devis_id: 7,
      decision_finale: "valide",
      decideur: "J. Martin",
      motif_decision: null,
      tentative_numero: 1,
      controle_bat_precedent_id: null,
      created_at: "2026-05-24T11:00:00",
    });

    render(<AtelierControleBatDetailPage />);
    await screen.findByTestId("bat-pdf");
    await userEvent.upload(
      screen.getByTestId("photo-input"),
      new File(["JPEG"], "t.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Analyser la conformité/i }),
    );
    await screen.findByTestId("resultat-controle");

    await userEvent.click(
      screen.getByRole("button", { name: /Valider la production/i }),
    );
    // Dialog Radix : titre rendu dans le portal.
    await waitFor(() =>
      expect(
        screen.getByText(/Valider la production — DEV-2026-0007/),
      ).toBeInTheDocument(),
    );

    await userEvent.type(
      screen.getByTestId("decideur-input"),
      "J. Martin",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: /^✅ Valider la production$/,
      }),
    );

    await waitFor(() =>
      expect(screen.getByTestId("decision-enregistree")).toBeInTheDocument(),
    );
    expect(decideControleMock).toHaveBeenCalledWith(100, {
      decision_finale: "valide",
      decideur: "J. Martin",
      motif_decision: undefined,
    });
    // Boutons d'action masqués après décision finale.
    expect(screen.queryByTestId("decision-actions")).toBeNull();
  });

  it("alerte_chef_atelier : bandeau rouge affiché en tête du résultat", async () => {
    useAuthMock.mockReturnValue({ user: buildUser() });
    getContextMock.mockResolvedValueOnce(buildContext());
    createControleMock.mockResolvedValueOnce(
      buildAnalyseResult({
        controle_id: 100,
        tentative: 4,
        score_conformite: "30.00",
        decision_recommandee: "rejeter",
        alerte_chef_atelier: true,
      }),
    );

    render(<AtelierControleBatDetailPage />);
    await screen.findByTestId("bat-pdf");
    await userEvent.upload(
      screen.getByTestId("photo-input"),
      new File(["JPEG"], "t.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /Analyser la conformité/i }),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("alerte-chef-atelier"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("alerte-chef-atelier")).toHaveTextContent(
      /Prévenir le chef d'atelier/i,
    );
  });
});
