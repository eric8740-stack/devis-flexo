import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ControleBatResult } from "@/lib/api/controleBat";

import { ResultatControle } from "./ResultatControle";

// Sprint 15 Lot D — tests RTL du composant ResultatControle.
// Vérifie l'ordre des sections, le tri des écarts par gravité, le bandeau
// rouge bloquant en cas d'alerte sens enroulement, et la conformité du
// rendu minimal (uniquement les champs renseignés sont affichés).

function buildResult(
  overrides: Partial<ControleBatResult> = {},
): ControleBatResult {
  // Aligné sur ControleBatAnalyseResponse : les listes (limites, ecarts,
  // conformes, manquants) sont TOUJOURS présentes côté backend (vides au
  // besoin), score_conformite/decision/etc. peuvent être null.
  return {
    controle_id: 101,
    devis_id: 7,
    tentative: 1,
    score_conformite: null,
    decision_recommandee: null,
    niveau_confiance: null,
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

describe("ResultatControle — Lot D", () => {
  it("header : identifiant contrôle + tentative toujours rendus", () => {
    render(<ResultatControle result={buildResult({ tentative: 3 })} />);
    expect(screen.getByTestId("resultat-controle")).toHaveTextContent(
      /contrôle #101/i,
    );
    expect(screen.getByTestId("resultat-controle")).toHaveTextContent(
      /tentative 3/i,
    );
  });

  it("score ≥85 : pastille verte + jauge meter à 92, décision valider", () => {
    render(
      <ResultatControle
        result={buildResult({
          // score_conformite : Decimal sérialisé string par Pydantic v2.
          score_conformite: "92.00",
          decision_recommandee: "valider",
        })}
      />,
    );
    const pastille = screen.getByTestId("score-pastille");
    expect(pastille).toHaveTextContent("92%");
    expect(pastille.className).toMatch(/emerald/);
    const jauge = screen.getByRole("meter");
    expect(jauge.getAttribute("aria-valuenow")).toBe("92");
    expect(screen.getByTestId("decision-valider")).toBeInTheDocument();
  });

  it("score 60-84 : pastille orange + décision ajuster_avant_demarrage", () => {
    render(
      <ResultatControle
        result={buildResult({
          score_conformite: "72.50",
          decision_recommandee: "ajuster_avant_demarrage",
        })}
      />,
    );
    const pastille = screen.getByTestId("score-pastille");
    expect(pastille.className).toMatch(/amber/);
    expect(
      screen.getByTestId("decision-ajuster_avant_demarrage"),
    ).toHaveTextContent(/Ajuster avant démarrage/i);
  });

  it("score <60 : pastille rouge + décision rejeter", () => {
    render(
      <ResultatControle
        result={buildResult({
          score_conformite: "45.00",
          decision_recommandee: "rejeter",
        })}
      />,
    );
    const pastille = screen.getByTestId("score-pastille");
    expect(pastille.className).toMatch(/red/);
    expect(screen.getByTestId("decision-rejeter")).toHaveTextContent(
      /Rejeter/i,
    );
  });

  it("écarts triés : critique avant majeur avant mineur, indépendant de l'ordre backend", () => {
    render(
      <ResultatControle
        result={buildResult({
          ecarts: [
            {
              type: "typo",
              gravite: "mineur",
              localisation: "Pied gauche",
              description: "Léger décalage typo",
              suggestion_correction: null,
            },
            {
              type: "couleur",
              gravite: "critique",
              localisation: "Centre",
              description: "Couleur manquante",
              suggestion_correction: "Refaire la plaque K",
            },
            {
              type: "nettete",
              gravite: "majeur",
              localisation: "Coin haut droit",
              description: "Logo flou",
              suggestion_correction: "Augmenter la résolution",
            },
          ],
        })}
      />,
    );
    const block = screen.getByTestId("ecarts-block");
    const cards = within(block).getAllByTestId(/^ecart-/);
    expect(cards.map((c) => c.getAttribute("data-testid"))).toEqual([
      "ecart-critique",
      "ecart-majeur",
      "ecart-mineur",
    ]);
    expect(cards[0]).toHaveTextContent(/Couleur manquante/);
    expect(cards[0]).toHaveTextContent(/Refaire la plaque K/);
  });

  it("0 écart : message 'Aucun écart détecté'", () => {
    render(<ResultatControle result={buildResult({ ecarts: [] })} />);
    expect(screen.getByTestId("ecarts-block")).toHaveTextContent(
      /Aucun écart/i,
    );
  });

  it("alerte sens enroulement : bandeau rouge bloquant en tête avec les 3 options + recommandée mise en avant", () => {
    const { container } = render(
      <ResultatControle
        result={buildResult({
          score_conformite: "30.00",
          decision_recommandee: "rejeter",
          sens_enroulement_demande: "SE3",
          sens_enroulement_detecte: "SE7",
          alerte_sens_enroulement: {
            message: "Le sens vu sur la photo ne correspond pas au demandé.",
            // Backend Lot 4 : place l'option `recommandee=true` en premier
            // (tri stable côté router) — l'UI rend l'ordre tel quel.
            options_correction: [
              {
                code: "ajustement_rebobineuse",
                libelle: "Ajuster la rebobineuse",
                description: "Inverser la sortie de la rebobineuse.",
                recommandee: true,
              },
              {
                code: "inversion_cliche",
                libelle: "Inverser le cliché",
                description: "Re-monter la plaque dans l'autre sens.",
                recommandee: false,
              },
              {
                code: "confirmation_client",
                libelle: "Confirmation client",
                description: "Appeler le client pour valider le sens livré.",
                recommandee: false,
              },
            ],
          },
        })}
      />,
    );

    const alerte = screen.getByTestId("alerte-sens-enroulement");
    expect(alerte).toHaveAttribute("role", "alert");
    expect(alerte).toHaveTextContent(/SE3/);
    expect(alerte).toHaveTextContent(/SE7/);
    expect(
      screen.getByTestId("option-correction-inversion_cliche"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("option-correction-ajustement_rebobineuse"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("option-correction-confirmation_client"),
    ).toBeInTheDocument();
    // Badge "Recommandée" visible UNIQUEMENT sur l'option recommandee=true.
    expect(
      screen.getByTestId("option-recommandee-ajustement_rebobineuse"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("option-recommandee-inversion_cliche"),
    ).toBeNull();
    expect(
      screen.queryByTestId("option-recommandee-confirmation_client"),
    ).toBeNull();

    // Bandeau alerte rendu AVANT le bloc score (ordre métier décisionnel).
    const allTestable = Array.from(
      container.querySelectorAll(
        "[data-testid='alerte-sens-enroulement'],[data-testid='score-decision']",
      ),
    );
    expect(
      allTestable.map((el) => el.getAttribute("data-testid")),
    ).toEqual(["alerte-sens-enroulement", "score-decision"]);

    // Quand l'alerte est présente, on ne re-rend pas le bloc "sens-sortie"
    // séparé (l'information est déjà dans l'alerte).
    expect(screen.queryByTestId("sens-sortie")).toBeNull();
  });

  it("sens cohérent (pas d'alerte) : bloc sens-sortie rendu avec demandé+détecté", () => {
    render(
      <ResultatControle
        result={buildResult({
          sens_enroulement_demande: "SE2",
          sens_enroulement_detecte: "SE2",
          alerte_sens_enroulement: null,
        })}
      />,
    );
    const bloc = screen.getByTestId("sens-sortie");
    expect(bloc).toHaveTextContent(/SE2/);
    expect(screen.queryByTestId("alerte-sens-enroulement")).toBeNull();
  });

  it("éléments conformes + manquants : 2 cards avec compteurs", () => {
    render(
      <ResultatControle
        result={buildResult({
          elements_conformes: ["Logo client", "Code-barres"],
          elements_manquants: ["Mention de tri"],
        })}
      />,
    );
    expect(screen.getByTestId("conformes-block")).toHaveTextContent(
      /Éléments conformes \(2\)/,
    );
    expect(screen.getByTestId("conformes-block")).toHaveTextContent(
      "Logo client",
    );
    expect(screen.getByTestId("manquants-block")).toHaveTextContent(
      /Éléments manquants \(1\)/,
    );
    expect(screen.getByTestId("manquants-block")).toHaveTextContent(
      "Mention de tri",
    );
  });

  it("niveau confiance + limites analyse : badge + liste affichés", () => {
    render(
      <ResultatControle
        result={buildResult({
          niveau_confiance: "moyen",
          limites_analyse: [
            "Photo légèrement floue",
            "Éclairage non uniforme",
          ],
        })}
      />,
    );
    expect(
      screen.getByTestId("niveau-confiance-moyen"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("confiance-limites")).toHaveTextContent(
      /Photo légèrement floue/,
    );
  });

  it("résultat minimal (listes vides + nulls) : pas de crash, sections optionnelles absentes", () => {
    render(<ResultatControle result={buildResult()} />);
    // Backend renvoie ecarts: [] → bloc rendu avec "Aucun écart"
    expect(screen.getByTestId("ecarts-block")).toBeInTheDocument();
    // Sections optionnelles absentes (champs nullables = null + listes vides)
    expect(screen.queryByTestId("score-decision")).toBeNull();
    expect(screen.queryByTestId("sens-sortie")).toBeNull();
    expect(screen.queryByTestId("alerte-sens-enroulement")).toBeNull();
    expect(screen.queryByTestId("conformes-block")).toBeNull();
    expect(screen.queryByTestId("manquants-block")).toBeNull();
    expect(screen.queryByTestId("confiance-limites")).toBeNull();
  });
});
