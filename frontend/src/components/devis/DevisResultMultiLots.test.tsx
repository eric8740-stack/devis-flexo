import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DevisDetail, LotProductionRead } from "@/lib/api";

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

  it("affiche le détail 7 postes par lot quand payload_output.details_par_lot est présent", () => {
    // LotProductionRead avec payload_visuel=null pour éviter de charger
    // SchemaImplantation (composant SACRED) dans ce test ciblé.
    const lot: LotProductionRead = {
      id: 10,
      ordre: 1,
      cylindre_id: 5,
      machine_id: 1,
      nb_poses_dev: 2,
      nb_poses_laize: 3,
      sens_enroulement: 1,
      quantite: 10000,
      matiere_id: 7,
      intervalle_dev_reel_mm: "2.5",
      intervalle_laize_reel_mm: "3.0",
      largeur_plaque_mm: "210.00",
      score_optim: 0.9,
      cout_lot_ht_eur: "400.00",
      created_at: "2026-05-27T10:00:00Z",
      updated_at: "2026-05-27T10:00:00Z",
      machine_nom: "MA-1",
      cylindre_nb_dents: 80,
      cylindre_developpe_mm: "254.00",
      matiere_libelle: "BOPP blanc 50µ",
      sens_enroulement_libelle: "Sens 1",
      rotation_vue_a_deg: 0,
      rotation_vue_c_deg: 0,
      payload_visuel: null,
    };
    render(
      <DevisResultMultiLots
        devis={buildDevis({
          ht_total_eur: "541.12",
          lots_production: [lot],
          payload_output: {
            mode: "multi-lots",
            prix_vente_ht_eur: "541.12",
            cout_revient_total_eur: "400.00",
            nb_lots: 1,
            details_par_lot: [
              {
                ordre: 1,
                prix_vente_ht_eur: "541.12",
                cout_revient_eur: "400.00",
                details: {
                  postes: [
                    { poste_numero: 1, libelle: "Matière", montant_eur: "120.00", details: {} },
                    { poste_numero: 2, libelle: "Encres", montant_eur: "80.00", details: {} },
                    { poste_numero: 3, libelle: "Clichés & outillage", montant_eur: "60.00", details: {} },
                    { poste_numero: 4, libelle: "Calage", montant_eur: "40.00", details: {} },
                    { poste_numero: 5, libelle: "Roulage", montant_eur: "50.00", details: {} },
                    { poste_numero: 6, libelle: "Finitions", montant_eur: "30.00", details: {} },
                    { poste_numero: 7, libelle: "Main-d'œuvre", montant_eur: "20.00", details: {} },
                  ],
                },
              },
            ],
          },
        })}
        pdfUrl="http://x/pdf"
        onDupliquer={noop}
        onSupprimer={noop}
      />,
    );

    // Le bloc breakdown du lot 1 est rendu, avec la table 7 postes.
    expect(
      screen.getByTestId("postes-breakdown-lot-1"),
    ).toBeInTheDocument();
    expect(screen.getByText("Détail des 7 postes")).toBeInTheDocument();
    // Quelques libellés métier visibles.
    expect(screen.getByText("Matière")).toBeInTheDocument();
    expect(screen.getByText("Clichés & outillage")).toBeInTheDocument();
    // Le total HT inchangé.
    expect(
      screen.getByText((content) => content.includes("541,12")),
    ).toBeInTheDocument();
  });

  it("pas de bloc breakdown quand details_par_lot est absent", () => {
    const lot: LotProductionRead = {
      id: 11,
      ordre: 1,
      cylindre_id: 5,
      machine_id: 1,
      nb_poses_dev: 2,
      nb_poses_laize: 3,
      sens_enroulement: 1,
      quantite: 5000,
      matiere_id: 7,
      intervalle_dev_reel_mm: null,
      intervalle_laize_reel_mm: null,
      largeur_plaque_mm: null,
      score_optim: null,
      cout_lot_ht_eur: "200.00",
      created_at: "2026-05-27T10:00:00Z",
      updated_at: "2026-05-27T10:00:00Z",
      machine_nom: "MA-1",
      cylindre_nb_dents: 80,
      cylindre_developpe_mm: "254.00",
      matiere_libelle: "BOPP blanc 50µ",
      sens_enroulement_libelle: "Sens 1",
      rotation_vue_a_deg: 0,
      rotation_vue_c_deg: 0,
      payload_visuel: null,
    };
    render(
      <DevisResultMultiLots
        devis={buildDevis({
          ht_total_eur: "200.00",
          lots_production: [lot],
          payload_output: { mode: "multi-lots" },
        })}
        pdfUrl="http://x/pdf"
        onDupliquer={noop}
        onSupprimer={noop}
      />,
    );

    expect(
      screen.queryByTestId("postes-breakdown-lot-1"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Détail des 7 postes")).not.toBeInTheDocument();
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
