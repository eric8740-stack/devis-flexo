import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ClientCreate } from "@/lib/api";

import { ClientForm } from "./ClientForm";

// Sprint 16 — tests Vitest pour la nouvelle section « Rebobinage » du
// formulaire client (3 booléens + 4 numériques + 2 texte). On ne mocke
// PAS l'API : ClientForm est purement contrôlé via le prop `onSubmit`,
// les pages create/edit étant celles qui appellent createClient /
// updateClient. Le test passe une `onSubmit` espionnée et inspecte le
// payload reçu.

const EMPTY_INITIAL: ClientCreate = {
  raison_sociale: "",
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
};

function buildClientRempli(): ClientCreate {
  return {
    ...EMPTY_INITIAL,
    raison_sociale: "ACME Étiquettes",
    marquage_bobine_requis: true,
    mandrin_fourni_par_client: false,
    film_protection_requis: true,
    diametre_mandrin_mm: 76,
    diametre_max_bobine_mm: 400,
    nb_etiq_par_bobine_fixe: 2500,
    sens_enroulement: 3,
    marquage_bobine_format: "Étiquette A6 face latérale",
    conditionnement_souhaite: "Carton renforcé export",
  };
}

describe("ClientForm — Sprint 16 section Rebobinage", () => {
  it("monte sans initial : section Rebobinage rendue, 3 checkboxes décochées, inputs vides", () => {
    render(<ClientForm onSubmit={vi.fn(async () => {})} />);

    // La section est rendue (testid sur la Card).
    expect(
      screen.getByTestId("client-rebobinage-section"),
    ).toBeInTheDocument();

    // 3 checkboxes décochées par défaut (server_default false côté backend).
    expect(
      screen.getByLabelText(/Marquage bobine requis/),
    ).not.toBeChecked();
    expect(
      screen.getByLabelText(/Mandrin fourni par le client/),
    ).not.toBeChecked();
    expect(
      screen.getByLabelText(/Film protection requis/),
    ).not.toBeChecked();

    // 4 inputs numériques vides (null → "" côté UI).
    expect(
      (screen.getByLabelText(/Ø Mandrin bobine/) as HTMLInputElement).value,
    ).toBe("");
    expect(
      (screen.getByLabelText(/Ø Max bobine livrée/) as HTMLInputElement)
        .value,
    ).toBe("");
    expect(
      (screen.getByLabelText(/Nb étiquettes \/ bobine/) as HTMLInputElement)
        .value,
    ).toBe("");
    expect(
      (screen.getByLabelText(/Sens d'enroulement/) as HTMLInputElement).value,
    ).toBe("");

    // 2 inputs texte vides.
    expect(
      (screen.getByLabelText(/Format du marquage/) as HTMLInputElement).value,
    ).toBe("");
    expect(
      (screen.getByLabelText(/Conditionnement souhaité/) as HTMLInputElement)
        .value,
    ).toBe("");
  });

  it("monte avec initial rempli : les 9 valeurs sont pré-remplies (cas édition)", () => {
    const initial = buildClientRempli();
    render(<ClientForm initial={initial} onSubmit={vi.fn(async () => {})} />);

    // 3 checkboxes selon les valeurs initiales.
    expect(screen.getByLabelText(/Marquage bobine requis/)).toBeChecked();
    expect(
      screen.getByLabelText(/Mandrin fourni par le client/),
    ).not.toBeChecked();
    expect(screen.getByLabelText(/Film protection requis/)).toBeChecked();

    // 4 inputs numériques pré-remplis.
    expect(
      (screen.getByLabelText(/Ø Mandrin bobine/) as HTMLInputElement).value,
    ).toBe("76");
    expect(
      (screen.getByLabelText(/Ø Max bobine livrée/) as HTMLInputElement)
        .value,
    ).toBe("400");
    expect(
      (screen.getByLabelText(/Nb étiquettes \/ bobine/) as HTMLInputElement)
        .value,
    ).toBe("2500");
    expect(
      (screen.getByLabelText(/Sens d'enroulement/) as HTMLInputElement).value,
    ).toBe("3");

    // 2 inputs texte pré-remplis.
    expect(
      (screen.getByLabelText(/Format du marquage/) as HTMLInputElement).value,
    ).toBe("Étiquette A6 face latérale");
    expect(
      (screen.getByLabelText(/Conditionnement souhaité/) as HTMLInputElement)
        .value,
    ).toBe("Carton renforcé export");
  });

  it("modification + submit : payload onSubmit contient les 9 champs avec les bonnes valeurs typées", async () => {
    const onSubmit = vi.fn(async () => {});
    render(<ClientForm onSubmit={onSubmit} />);

    // Raison sociale (requise pour passer le HTML required côté form).
    await userEvent.type(
      screen.getByLabelText(/Raison sociale/),
      "ACME Étiquettes",
    );

    // Coche 2 des 3 booléens.
    await userEvent.click(screen.getByLabelText(/Marquage bobine requis/));
    await userEvent.click(screen.getByLabelText(/Film protection requis/));

    // Renseigne les 4 numériques.
    await userEvent.type(screen.getByLabelText(/Ø Mandrin bobine/), "76");
    await userEvent.type(
      screen.getByLabelText(/Ø Max bobine livrée/),
      "400",
    );
    await userEvent.type(
      screen.getByLabelText(/Nb étiquettes \/ bobine/),
      "2500",
    );
    await userEvent.type(screen.getByLabelText(/Sens d'enroulement/), "3");

    // Renseigne les 2 textes.
    await userEvent.type(
      screen.getByLabelText(/Format du marquage/),
      "Étiquette A6",
    );
    await userEvent.type(
      screen.getByLabelText(/Conditionnement souhaité/),
      "Carton renforcé",
    );

    await userEvent.click(
      screen.getByRole("button", { name: /Enregistrer/i }),
    );

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0]?.[0] as ClientCreate;

    // Les 9 champs sont dans le payload avec les bonnes valeurs et types.
    expect(payload.marquage_bobine_requis).toBe(true);
    expect(payload.mandrin_fourni_par_client).toBe(false);
    expect(payload.film_protection_requis).toBe(true);
    expect(payload.diametre_mandrin_mm).toBe(76);
    expect(payload.diametre_max_bobine_mm).toBe(400);
    expect(payload.nb_etiq_par_bobine_fixe).toBe(2500);
    expect(payload.sens_enroulement).toBe(3);
    expect(payload.marquage_bobine_format).toBe("Étiquette A6");
    expect(payload.conditionnement_souhaite).toBe("Carton renforcé");

    // Sanity check : les types sont bien `number` et pas `string` pour les
    // 4 numériques (cf. parseNumOrNull). Pas de `"76"` qui pourrait passer
    // par Pydantic mais polluer le typage côté UI.
    expect(typeof payload.diametre_mandrin_mm).toBe("number");
    expect(typeof payload.sens_enroulement).toBe("number");
  });

  it("input numérique vidé après saisie : repasse à null dans le payload (pas 0, pas NaN)", async () => {
    const onSubmit = vi.fn(async () => {});
    render(
      <ClientForm
        initial={buildClientRempli()}
        onSubmit={onSubmit}
      />,
    );

    // L'utilisateur efface le diamètre mandrin (clear sur l'input).
    const inputMandrin = screen.getByLabelText(
      /Ø Mandrin bobine/,
    ) as HTMLInputElement;
    await userEvent.clear(inputMandrin);
    expect(inputMandrin.value).toBe("");

    await userEvent.click(
      screen.getByRole("button", { name: /Enregistrer/i }),
    );

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0]?.[0] as ClientCreate;
    expect(payload.diametre_mandrin_mm).toBeNull();
    // Les autres champs (non touchés) gardent leur valeur initiale.
    expect(payload.diametre_max_bobine_mm).toBe(400);
  });

  it("décocher un booléen pré-coché : payload reflète le changement (true → false)", async () => {
    const onSubmit = vi.fn(async () => {});
    render(
      <ClientForm
        initial={buildClientRempli()}
        onSubmit={onSubmit}
      />,
    );

    const checkbox = screen.getByLabelText(/Marquage bobine requis/);
    expect(checkbox).toBeChecked();
    await userEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();

    await userEvent.click(
      screen.getByRole("button", { name: /Enregistrer/i }),
    );

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0]?.[0] as ClientCreate;
    expect(payload.marquage_bobine_requis).toBe(false);
    // Les autres booléens (non touchés) gardent leur valeur initiale.
    expect(payload.film_protection_requis).toBe(true);
  });
});
