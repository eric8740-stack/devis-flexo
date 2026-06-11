import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DevisPageUnique from "./page";

const routerPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush }),
}));

let fetchSpy: ReturnType<typeof vi.fn>;

function installFetchMock() {
  fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const ok = (body: unknown, status = 200) =>
      ({ ok: true, status, statusText: "OK", json: async () => body }) as Response;

    if (url.includes("/api/matieres")) {
      return ok([
        {
          id: 1,
          code: "PET50",
          libelle: "PET",
          categorie: null,
          sous_type: null,
          grammage_gm2: null,
          epaisseur_microns: 50,
          est_transparent: false,
          opacite_pct: null,
          certifications_sanitaires: null,
          certifications_env: null,
          adhesifs_compatibles: null,
          actif: true,
        },
      ]);
    }
    if (url.includes("/api/cylindres")) {
      return ok([
        {
          id: 1,
          nb_dents: 104,
          developpe_mm: "330.20",
          actif: true,
          notes: null,
          date_creation: "",
        },
      ]);
    }
    if (url.includes("/api/machines")) {
      return ok([
        { id: 1, nom: "Mark Andy P5", actif: true, laize_max_mm: "330" },
      ]);
    }
    if (url.includes("/api/optimisation/options-disponibles")) {
      return ok([
        {
          id: 1,
          code: "VERNIS",
          libelle: "Vernis",
          categorie: null,
          coef_vitesse_impact: 0,
          coef_gache_impact: 0,
        },
        {
          id: 2,
          code: "DORURE",
          libelle: "Dorure",
          categorie: null,
          coef_vitesse_impact: 0,
          coef_gache_impact: 0,
        },
      ]);
    }
    if (url.includes("/api/clients")) {
      return ok([
        {
          id: 7,
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
          diametre_mandrin_mm: 152,
          diametre_max_bobine_mm: 400,
          nb_etiq_par_bobine_fixe: null,
          sens_enroulement: 3,
          marquage_bobine_format: null,
          conditionnement_souhaite: null,
        },
      ]);
    }
    if (url.includes("/api/entreprise")) {
      return ok({ chute_laterale_min_mm: "10" });
    }
    if (/\/api\/matieres\/\d+$/.test(url) && method === "PATCH") {
      const body = JSON.parse((init?.body as string) ?? "{}");
      return ok({
        id: 1,
        libelle: "PET",
        epaisseur_microns: body.epaisseur_microns,
      });
    }
    if (url.endsWith("/api/devis/preview") && method === "POST") {
      const body = JSON.parse((init?.body as string) ?? "{}");
      const sansOutil = body.mode_sans_outil === true;
      // V0 — remise calculée depuis la requête (mock).
      const prixHt = 123.45;
      const remisePct = Number(body.remise_pct) || 0;
      const remiseEur = (prixHt * remisePct) / 100;
      const prixHtNet = prixHt - remiseEur;
      // Réponse wire : Decimal sérialisés en CHAÎNES, nullables.
      return ok({
        prix_ht: "123.45",
        cout_revient: "80.00",
        marge_pct: "30.00",
        prix_1000: "12.35",
        remise_pct: remisePct.toFixed(2),
        remise_eur: remiseEur.toFixed(2),
        prix_ht_net: prixHtNet.toFixed(2),
        bobinage: {
          ml_total: 412.5,
          m2_total: 94.9,
          ml_par_bobine: Number(body.ml_par_bobine) || 2000,
          nb_bobines: 2,
          // Ø dépasse la presse au-delà d'une grosse quantité (pour le bandeau).
          diametre_bobine_mm: Number(body.quantite) > 50000 ? 1200 : 291,
          diametre_mandrin_mm: Number(body.mandrin_mm) || 76,
          diametre_max_presse_mm: 1100,
          depasse_max: Number(body.quantite) > 50000,
          nb_changements: 1,
          temps_arret_min: 15,
        },
        decompo_groupee: {
          matiere_p1: "40.00",
          impression_presse_calage: "25.00",
          cliches_outil: "10.00",
          option_finitions: "0.00",
          refente: sansOutil ? "8.00" : "0.00",
        },
        geometrie: sansOutil
          ? {
              diametre_mm: 250,
              nb_poses: 3,
              nb_filles: 3,
              dechet_lateral_mm: 24.0,
              // Lot E — fallback tant qu'aucune matière n'est choisie.
              epaisseur_utilisee_microns: Number(body.epaisseur_um) || 150,
              epaisseur_fallback: body.matiere_id == null,
            }
          : {
              diametre_mm: 250,
              nb_poses: 12,
              nb_filles: null,
              dechet_lateral_mm: null,
              epaisseur_utilisee_microns: Number(body.epaisseur_um) || 150,
              epaisseur_fallback: body.matiere_id == null,
            },
        decompo: sansOutil
          ? [
              { poste: "Matière", montant: "40.00" },
              { poste: "Refente (rebobinage)", montant: "8.00" },
            ]
          : [
              { poste: "Matière", montant: "40.00" },
              { poste: "Encres", montant: "20.00" },
            ],
        options: [
          { code: "VERNIS", delta_eur: "12.00", impact_production: false },
          { code: "DORURE", delta_eur: null, impact_production: true },
          { code: "couleur_plus", delta_eur: "5.50", impact_production: false },
        ],
        alertes: sansOutil ? [] : [],
        // Lot C — configs outil×machine + écarts (vides en sans outil).
        configs: sansOutil
          ? []
          : [
              {
                id: 11,
                cylindre_dents: 104,
                developpe_mm: 330.2,
                machine: "Mark Andy P5",
                poses_laize: 2,
                poses_dev: 4,
                poses_total: 8,
                delta_dev_mm: 2.55,
                delta_laize_mm: 5,
                sens: 1,
                score: 100,
                recommande: true,
              },
              {
                id: 12,
                cylindre_dents: 132,
                developpe_mm: 419.1,
                machine: "Mark Andy P5",
                poses_laize: 2,
                poses_dev: 5,
                poses_total: 10,
                delta_dev_mm: 3.82,
                delta_laize_mm: 5,
                sens: 1,
                score: 85,
                recommande: true,
              },
            ],
        ecarts: sansOutil
          ? null
          : {
              intervalle_laize_mm: 5,
              intervalle_dev_mm: 2,
              nb_poses_laize: "auto",
              force_intervalle_laize: false,
            },
      });
    }
    if (url.endsWith("/api/devis") && method === "POST") {
      return ok({ id: 999, numero: "DEV-2026-0999" }, 201);
    }
    throw new Error(`No mock for ${method} ${url}`);
  });
  global.fetch = fetchSpy as unknown as typeof fetch;
}

function postDevisBody() {
  const call = fetchSpy.mock.calls.find(
    (c) =>
      String(c[0]).endsWith("/api/devis") &&
      (c[1] as RequestInit)?.method === "POST",
  );
  return JSON.parse((call?.[1] as RequestInit).body as string);
}

describe("DevisPageUnique — page devis réactive", () => {
  beforeEach(() => {
    window.localStorage.clear();
    routerPush.mockReset();
    installFetchMock();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hero prix rendu en direct dès le montage (estimation live)", async () => {
    render(<DevisPageUnique />);
    const valeur = await screen.findByTestId("hero-prix-valeur");
    expect(valeur).toHaveTextContent("€");
  });

  it("toggle sans outil : replie la carte Outil (transition), expose la laize stock", async () => {
    render(<DevisPageUnique />);
    // Avec outil par défaut → section Outil ouverte (config cards visibles).
    await screen.findByTestId("config-card-11");
    expect(screen.getByTestId("outil-section")).not.toHaveAttribute(
      "aria-hidden",
      "true",
    );
    expect(screen.getByTestId("sans-outil-fields")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
    await userEvent.click(screen.getByTestId("toggle-sans-outil"));
    // La carte Outil reste montée mais repliée (aria-hidden true) ; les champs
    // sans-outil s'ouvrent.
    expect(screen.getByTestId("outil-section")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
    expect(screen.getByTestId("sans-outil-fields")).not.toHaveAttribute(
      "aria-hidden",
      "true",
    );
    expect(screen.getByTestId("laize-stock")).toBeInTheDocument();
  });

  it("sélection client → pré-remplit le profil bobine (mandrin, Ø max, sens)", async () => {
    render(<DevisPageUnique />);
    await screen.findByRole("option", { name: "ACME Étiquettes" });
    await userEvent.selectOptions(screen.getByTestId("d-client"), "7");
    await waitFor(() =>
      expect(screen.getByTestId("b-mandrin")).toHaveValue(152),
    );
    expect(screen.getByTestId("b-diametre-max")).toHaveValue(400);
    expect(screen.getByTestId("b-sens")).toHaveValue(3);
  });

  it("chips finitions : « +X € » par code, aria-pressed au toggle, impact production", async () => {
    render(<DevisPageUnique />);
    const vernis = await screen.findByTestId("fin-VERNIS");
    // Coût marginal serveur affiché (options[].delta_eur par code).
    await waitFor(() => expect(vernis).toHaveTextContent("+12,00 €"));
    expect(vernis).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(vernis);
    expect(vernis).toHaveAttribute("aria-pressed", "true");
    // Option à impact production sans forfait → jamais « +0 € ».
    expect(screen.getByTestId("fin-DORURE")).toHaveTextContent(
      /impact production/i,
    );
    // couleur_plus rendu de la même façon.
    expect(screen.getByTestId("couleur-plus")).toHaveTextContent("+5,50 €");
  });

  it("Section 2 : cartes configs (top recommandé auto-sélectionné) + table dépliable + écarts", async () => {
    render(<DevisPageUnique />);
    // Top score (config 11) auto-sélectionnée.
    await waitFor(() =>
      expect(screen.getByTestId("config-card-11")).toHaveAttribute(
        "aria-pressed",
        "true",
      ),
    );
    expect(screen.getByTestId("config-card-12")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    // Sélection d'une autre config.
    await userEvent.click(screen.getByTestId("config-card-12"));
    expect(screen.getByTestId("config-card-12")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("config-card-11")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    // Table repliée par défaut, dépliable.
    expect(screen.getByTestId("configs-table")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
    await userEvent.click(screen.getByTestId("toggle-configs"));
    expect(screen.getByTestId("configs-table")).not.toHaveAttribute(
      "aria-hidden",
      "true",
    );
    // Écarts : intervalle laize désactivé tant que non forcé.
    expect(screen.getByTestId("ec-intervalle-laize")).toBeDisabled();
    await userEvent.click(screen.getByTestId("ec-force-laize"));
    expect(screen.getByTestId("ec-intervalle-laize")).not.toBeDisabled();
  });

  it("V0 : panneau (HT net + décompo groupée + total) + barre mobile + remise live", async () => {
    render(<DevisPageUnique />);
    await screen.findByTestId("hero-prix-valeur");
    // Le gros prix = HT net (123,45 € sans remise au départ).
    expect(screen.getByTestId("hero-prix-valeur")).toHaveTextContent("123,45");
    // Décompo coût groupée (avec ligne Total) affichée dans le panneau.
    expect(screen.getByTestId("hero-decompo-groupee")).toHaveTextContent(
      /Total HT/,
    );
    // Barre prix basse fixe (mobile) présente, avec son propre Valider.
    expect(screen.getByTestId("mobile-bar")).toBeInTheDocument();
    expect(screen.getByTestId("valider-mobile")).toBeInTheDocument();
    // Pas de remise par défaut (0 %).
    expect(screen.queryByTestId("hero-remise")).toBeNull();
    // Saisir une remise → ligne remise (HT brut + −€) + HT net recalculé.
    await userEvent.clear(screen.getByTestId("c-remise"));
    await userEvent.type(screen.getByTestId("c-remise"), "10");
    await waitFor(() =>
      expect(screen.getByTestId("hero-remise")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("hero-remise")).toHaveTextContent(/remise/i);
    // Le gros prix = HT net < brut → n'affiche plus 123,45 €.
    await waitFor(() =>
      expect(screen.getByTestId("hero-prix-valeur")).not.toHaveTextContent(
        "123,45",
      ),
    );
  });

  it("Lot E : bandeau fallback épaisseur + Ø live + enregistrement catalogue (PATCH)", async () => {
    render(<DevisPageUnique />);
    // Aucune matière au départ → fallback épaisseur visible + Ø live affiché.
    await waitFor(() =>
      expect(screen.getByTestId("m-fallback")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("m-diametre")).toHaveTextContent(/250 mm/);
    // Choisir une matière → le fallback se lève.
    await userEvent.selectOptions(screen.getByTestId("m-matiere"), "1");
    await waitFor(() =>
      expect(screen.queryByTestId("m-fallback")).toBeNull(),
    );
    // Enregistrer l'épaisseur au catalogue → PATCH /api/matieres/1.
    await userEvent.click(screen.getByTestId("m-save-epaisseur"));
    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(
          (c) =>
            /\/api\/matieres\/1$/.test(String(c[0])) &&
            (c[1] as RequestInit)?.method === "PATCH",
        ),
      ).toBe(true),
    );
  });

  it("Lot F : appro m² + plan bobines + bandeau dépassement Ø max presse", async () => {
    render(<DevisPageUnique />);
    // Besoin matière à commander (m²) dans la carte Matière.
    await waitFor(() =>
      expect(screen.getByTestId("m-appro")).toHaveTextContent(/m²/),
    );
    // Plan bobines (nb_bobines / Ø / temps).
    expect(screen.getByTestId("b-plan")).toHaveTextContent(/bobine/);
    // Pas de dépassement au format par défaut.
    expect(screen.queryByTestId("b-depasse-max")).toBeNull();
    // Grosse quantité → Ø bobine dépasse la presse → bandeau visible.
    await userEvent.clear(screen.getByTestId("f-qte"));
    await userEvent.type(screen.getByTestId("f-qte"), "100000");
    await waitFor(() =>
      expect(screen.getByTestId("b-depasse-max")).toBeInTheDocument(),
    );
  });

  it("décompo refente affichée en sans outil (déchet latéral)", async () => {
    render(<DevisPageUnique />);
    await screen.findByTestId("toggle-sans-outil");
    await userEvent.click(screen.getByTestId("toggle-sans-outil"));
    await userEvent.type(screen.getByTestId("laize-stock"), "330");
    await waitFor(() =>
      expect(screen.getByTestId("decompo-dechet")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("decompo-dechet")).toHaveTextContent(/déchet/i);
  });

  it("Valider (avec outil) → POST /api/devis avec le cylindre_id de la config", async () => {
    const { container } = render(<DevisPageUnique />);
    // Config recommandée auto-sélectionnée → résout cylindre/machine (parc).
    await screen.findByTestId("config-card-11");
    await userEvent.selectOptions(screen.getByTestId("m-matiere"), "1");

    await waitFor(() =>
      expect(screen.getByTestId("valider")).not.toBeDisabled(),
    );
    // jsdom : submit via le form (le click sur bouton submit ne déclenche pas
    // toujours l'événement submit en environnement de test).
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(
          (c) =>
            String(c[0]).endsWith("/api/devis") &&
            (c[1] as RequestInit)?.method === "POST",
        ),
      ).toBe(true),
    );
    const body = postDevisBody();
    expect(body.lots[0].cylindre_id).toBe(1);
    expect(body.lots[0].machine_id).toBe(1);
    expect(body.lots[0].matiere_id).toBe(1);
    expect(body.payload_input.mode_sans_outil).toBe(false);
    expect(routerPush).toHaveBeenCalledWith("/devis/999");
  });

  it("Valider (sans outil) → cylindre_id null + mode_sans_outil true", async () => {
    const { container } = render(<DevisPageUnique />);
    await screen.findByTestId("toggle-sans-outil");
    await userEvent.click(screen.getByTestId("toggle-sans-outil"));
    await userEvent.type(screen.getByTestId("laize-stock"), "330");
    // Attendre le chargement des matières (Promise.all au mount).
    await screen.findByRole("option", { name: "PET" });
    await userEvent.selectOptions(screen.getByTestId("m-matiere"), "1");

    await waitFor(() =>
      expect(screen.getByTestId("valider")).not.toBeDisabled(),
    );
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(
          (c) =>
            String(c[0]).endsWith("/api/devis") &&
            (c[1] as RequestInit)?.method === "POST",
        ),
      ).toBe(true),
    );
    const body = postDevisBody();
    expect(body.lots[0].cylindre_id).toBeNull();
    expect(body.payload_input.mode_sans_outil).toBe(true);
    expect(body.payload_input.laize_stock_mm).toBe(330);
  });
});
