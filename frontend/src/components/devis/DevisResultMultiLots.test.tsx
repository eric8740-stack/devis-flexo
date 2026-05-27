import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DevisDetail } from "@/lib/api";

import { DevisResultMultiLots } from "./DevisResultMultiLots";

// Fix bandeau erreur chiffrage — on vérifie que :
//   - chiffrage OK (ht_total_eur renseigné)        → prix affiché, pas de bandeau
//   - chiffrage incomplet (ht_total_eur NULL)      → bandeau d'erreur, JAMAIS « 0,00 € »
//   - message lu en repli sur payload_output.chiffrage_auto_erreur
// On monte le composant avec lots_production vide : la logique prix/bandeau
// du récap hero ne dépend pas des lots (juste de ht_total_eur), ça évite de
// tirer SchemaImplantation (composant SACRED) dans ce test ciblé.

function buildDevis(overrides: Partial<DevisDetail> = {}): DevisDetail {
  return {
    id: 999,
    numero: "DEV-2026-0999",
    date_creation: "2026-05-27T10:00:00Z",
    date_modification: "2026-05-27T10:00:00Z",
    statut: "brouillon",
    client_id: null,
    client_nom: null,
    machine_id: 1,
    machine_nom: "MA-1",
    payload_input: {},
    payload_output: { mode: "multi-lots" },
    mode_calcul: "manuel",
    cylindre_choisi_z: null,
    cylindre_choisi_nb_etiq: null,
    format_h_mm: "80",
    format_l_mm: "100",
    ht_total_eur: "1234.56",
    reduction_pct: "0",
    lots_production: [],
    ...overrides,
  };
}

const noop = () => {};

describe("DevisResultMultiLots — bandeau erreur chiffrage", () => {
  it("chiffrage OK : affiche le prix, pas de bandeau d'erreur", () => {
    render(
      <DevisResultMultiLots
        devis={buildDevis({ ht_total_eur: "1234.56" })}
        pdfUrl="http://x/pdf"
        onDupliquer={noop}
        onSupprimer={noop}
      />,
    );

    expect(
      screen.getByText((content) => content.includes("234,56")),
    ).toBeInTheDocument();
    expect(screen.getByText(/Coût total HT/i)).toBeInTheDocument();
    expect(
      screen.queryByTestId("chiffrage-erreur-bandeau"),
    ).not.toBeInTheDocument();
  });

  it("ht_total_eur NULL + chiffrage_auto_erreur top-level : bandeau, jamais 0 euro", () => {
    render(
      <DevisResultMultiLots
        devis={buildDevis({
          ht_total_eur: null,
          chiffrage_auto_erreur:
            "Complexe id=1 (BOPP_BLANC_50) n'a pas de grammage_g_m2 défini, requis pour P1",
        })}
        pdfUrl="http://x/pdf"
        onDupliquer={noop}
        onSupprimer={noop}
      />,
    );

    const bandeau = screen.getByTestId("chiffrage-erreur-bandeau");
    expect(bandeau).toHaveTextContent(/Chiffrage incomplet/i);
    expect(bandeau).toHaveTextContent(/grammage_g_m2/);
    // Aucun montant « 0,00 » trompeur dans tout le rendu.
    expect(
      screen.queryByText((content) => content.includes("0,00")),
    ).not.toBeInTheDocument();
    // Le libellé du prix valide n'est pas monté.
    expect(screen.queryByText(/Coût total HT/i)).not.toBeInTheDocument();
  });

  it("ht_total_eur NULL sans top-level : repli sur payload_output.chiffrage_auto_erreur", () => {
    render(
      <DevisResultMultiLots
        devis={buildDevis({
          ht_total_eur: null,
          payload_output: {
            mode: "multi-lots",
            chiffrage_auto_erreur: "Erreur stockée dans payload_output",
          },
        })}
        pdfUrl="http://x/pdf"
        onDupliquer={noop}
        onSupprimer={noop}
      />,
    );

    const bandeau = screen.getByTestId("chiffrage-erreur-bandeau");
    expect(bandeau).toHaveTextContent(/Erreur stockée dans payload_output/);
    expect(
      screen.queryByText((content) => content.includes("0,00")),
    ).not.toBeInTheDocument();
  });
});
