import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DevisDetail, LotProductionRead } from "@/lib/api";

import { DevisResultMultiLots } from "./DevisResultMultiLots";

// PlanificateurBobines (rendu via LotCard sur les lots multi-lots) consomme
// `useRouter()` de next/navigation. Mock minimal pour que le rendu n'éclate
// pas en environnement test (« invariant expected app router to be mounted »).
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Bug #6 (6.2c) — SchemaImplantation (SACRED, SVG) réduit à un placeholder
// pour tester l'affichage du Ø/badge réel sans le rendu SVG. Les tests
// existants utilisent `payload_visuel: null` → non impactés.
vi.mock("@/components/SchemaImplantation", () => ({
  SchemaImplantation: () => <div data-testid="schema-implantation" />,
}));

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

  it("affiche le rapport de fabrication (récap + 7 postes) quand details_par_lot est présent", () => {
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
                // CoutLot.ordre est 0-indexé côté backend (vs LotProduction.ordre
                // 1-indexé). L'alignement front est positional, pas par ordre.
                ordre: 0,
                prix_vente_ht_eur: "541.12",
                cout_revient_eur: "400.00",
                details: {
                  prix_vente_ht_eur: "541.12",
                  cout_revient_eur: "400.00",
                  pct_marge_appliquee: "0.35",
                  prix_au_mille_eur: "54.11",
                  postes: [
                    {
                      poste_numero: 1,
                      libelle: "Matière",
                      montant_eur: "120.00",
                      details: { surface_support_m2: 200 },
                    },
                    { poste_numero: 2, libelle: "Encres", montant_eur: "80.00", details: {} },
                    { poste_numero: 3, libelle: "Clichés & outillage", montant_eur: "60.00", details: {} },
                    { poste_numero: 4, libelle: "Calage", montant_eur: "40.00", details: {} },
                    {
                      poste_numero: 5,
                      libelle: "Roulage",
                      montant_eur: "50.00",
                      details: { ml_total: 3000 },
                    },
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

    // Le bloc rapport de fabrication du lot 1 est rendu.
    expect(
      screen.getByTestId("rapport-fabrication-lot-1"),
    ).toBeInTheDocument();
    // Section Récapitulatif mise en avant.
    const recap = screen.getByTestId("recapitulatif-lot");
    expect(recap).toHaveTextContent("Prix de vente HT");
    expect(recap).toHaveTextContent("Coût de revient");
    expect(recap).toHaveTextContent("Marge appliquée");
    expect(recap).toHaveTextContent(/35,0 %/);
    // Ratios pied : prix au mille / €/ml / €/m².
    expect(recap).toHaveTextContent(/Prix au mille/i);
    expect(recap).toHaveTextContent(/par mètre linéaire/i);
    expect(recap).toHaveTextContent(/par m² imprimé/i);
    // Section 7 postes + libellés métier visibles.
    expect(screen.getByText("Détail des 7 postes")).toBeInTheDocument();
    expect(screen.getByText("Matière")).toBeInTheDocument();
    expect(screen.getByText("Clichés & outillage")).toBeInTheDocument();
    // Le total HT inchangé (apparaît dans le récap ET dans le hero).
    expect(
      screen.getAllByText((content) => content.includes("541,12")).length,
    ).toBeGreaterThan(0);
  });

  it("aligne le chiffrage par position (multi-lots) même si les ordres divergent", () => {
    // Régression off-by-one : LotProduction.ordre est 1-indexé (DB), CoutLot.ordre
    // est 0-indexé (agrégateur). Le rendu doit s'aligner par POSITION, pas par
    // valeur d'ordre, sinon le rapport ne s'affiche pour aucun lot.
    const baseLot = (id: number, ordre: number): LotProductionRead => ({
      id,
      ordre,
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
      matiere_libelle: "BOPP",
      sens_enroulement_libelle: "Sens 1",
      rotation_vue_a_deg: 0,
      rotation_vue_c_deg: 0,
      payload_visuel: null,
    });
    const makePoste = (n: number, libelle: string, montant: string) => ({
      poste_numero: n,
      libelle,
      montant_eur: montant,
      details: {} as Record<string, number | string | null>,
    });
    render(
      <DevisResultMultiLots
        devis={buildDevis({
          ht_total_eur: "1000.00",
          lots_production: [baseLot(10, 1), baseLot(11, 2)],
          payload_output: {
            mode: "multi-lots",
            details_par_lot: [
              {
                ordre: 0, // 0-indexé backend, 1er lot
                prix_vente_ht_eur: "400.00",
                cout_revient_eur: "300.00",
                details: {
                  prix_vente_ht_eur: "400.00",
                  cout_revient_eur: "300.00",
                  pct_marge_appliquee: "0.30",
                  prix_au_mille_eur: "80.00",
                  postes: [
                    makePoste(1, "Matière LotA", "100.00"),
                    makePoste(2, "Encres", "0.00"),
                    makePoste(3, "Clichés", "0.00"),
                    makePoste(4, "Calage", "100.00"),
                    makePoste(5, "Roulage", "50.00"),
                    makePoste(6, "Finitions", "30.00"),
                    makePoste(7, "MO", "20.00"),
                  ],
                },
              },
              {
                ordre: 1, // 0-indexé backend, 2e lot
                prix_vente_ht_eur: "600.00",
                cout_revient_eur: "500.00",
                details: {
                  prix_vente_ht_eur: "600.00",
                  cout_revient_eur: "500.00",
                  pct_marge_appliquee: "0.20",
                  prix_au_mille_eur: "120.00",
                  postes: [
                    makePoste(1, "Matière LotB", "200.00"),
                    makePoste(2, "Encres", "50.00"),
                    makePoste(3, "Clichés", "60.00"),
                    makePoste(4, "Calage", "100.00"),
                    makePoste(5, "Roulage", "50.00"),
                    makePoste(6, "Finitions", "30.00"),
                    makePoste(7, "MO", "10.00"),
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
    // Les deux blocs rapport sont rendus (key = lot.ordre, donc 1 et 2).
    expect(screen.getByTestId("rapport-fabrication-lot-1")).toBeInTheDocument();
    expect(screen.getByTestId("rapport-fabrication-lot-2")).toBeInTheDocument();
    // Alignement positional : le 1er lot reçoit "Matière LotA", le 2e "LotB".
    expect(screen.getByText("Matière LotA")).toBeInTheDocument();
    expect(screen.getByText("Matière LotB")).toBeInTheDocument();
  });

  it("pas de bloc rapport quand details_par_lot est absent", () => {
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
      screen.queryByTestId("rapport-fabrication-lot-1"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Détail des 7 postes")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("recapitulatif-lot"),
    ).not.toBeInTheDocument();
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

describe("DevisResultMultiLots — Ø multilots réel (bug #6 6.2c)", () => {
  function lotAvecVisuel(
    payload_visuel: Record<string, unknown> | null,
  ): LotProductionRead {
    return {
      id: 1,
      ordre: 1,
      cylindre_id: 1,
      machine_id: 1,
      nb_poses_dev: 2,
      nb_poses_laize: 5,
      sens_enroulement: 1,
      quantite: 12000,
      matiere_id: 1,
      intervalle_dev_reel_mm: "2",
      intervalle_laize_reel_mm: "2",
      largeur_plaque_mm: "200",
      score_optim: 100,
      cout_lot_ht_eur: "100.00",
      created_at: "2026-05-27T10:00:00Z",
      updated_at: "2026-05-27T10:00:00Z",
      machine_nom: "MA-1",
      cylindre_nb_dents: 104,
      cylindre_developpe_mm: "330",
      matiere_libelle: "PET blanc 50µ",
      sens_enroulement_libelle: "Sens 1",
      rotation_vue_a_deg: 0,
      rotation_vue_c_deg: 0,
      payload_visuel,
    };
  }

  it("payload_visuel enrichi → badge source + Ø bobine/départ affichés", () => {
    render(
      <DevisResultMultiLots
        devis={buildDevis({
          ht_total_eur: "100.00",
          lots_production: [
            lotAvecVisuel({
              diametre_bobine_mm: 305,
              diametre_depart_mm: 82,
              epaisseur_effective_um: 90,
              epaisseur_source: "matiere",
              paroi_mm: 3,
              epaisseur_appliquee_um: 150,
            }),
          ],
        })}
        pdfUrl="http://x/pdf"
        onDupliquer={noop}
        onSupprimer={noop}
      />,
    );

    const badge = screen.getByTestId("lot-diametre-source-1");
    expect(badge).toHaveTextContent(/matière/i);
    expect(badge).toHaveTextContent(/90 µm/);
    const echo = screen.getByTestId("lot-diametre-echo-1");
    expect(echo).toHaveTextContent("305 mm"); // Ø bobine réel (≠ candidat)
    expect(echo).toHaveTextContent(/82 mm/); // Ø départ (mandrin + 2×paroi)
    expect(echo).toHaveTextContent(/paroi 3 mm/);
  });

  it("payload_visuel candidat figé (sans écho) → pas de badge source", () => {
    render(
      <DevisResultMultiLots
        devis={buildDevis({
          ht_total_eur: "100.00",
          lots_production: [
            lotAvecVisuel({
              diametre_bobine_mm: 300,
              epaisseur_appliquee_um: 150,
            }),
          ],
        })}
        pdfUrl="http://x/pdf"
        onDupliquer={noop}
        onSupprimer={noop}
      />,
    );

    expect(
      screen.queryByTestId("lot-diametre-source-1"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("lot-diametre-echo-1"),
    ).not.toBeInTheDocument();
  });
});
