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
  return {
    controle_id: 101,
    devis_id: 7,
    tentative: 1,
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
          score_conformite: 92,
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

  it("score 60-84 : pastille orange + décision ajuster", () => {
    render(
      <ResultatControle
        result={buildResult({
          score_conformite: 72,
          decision_recommandee: "ajuster",
        })}
      />,
    );
    const pastille = screen.getByTestId("score-pastille");
    expect(pastille.className).toMatch(/amber/);
    expect(screen.getByTestId("decision-ajuster")).toBeInTheDocument();
  });

  it("score <60 : pastille rouge + décision rejeter", () => {
    render(
      <ResultatControle
        result={buildResult({
          score_conformite: 45,
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
              gravite: "mineur",
              localisation: "Pied gauche",
              description: "Léger décalage typo",
              suggestion_correction: null,
            },
            {
              gravite: "critique",
              localisation: "Centre",
              description: "Couleur manquante",
              suggestion_correction: "Refaire la plaque K",
            },
            {
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

  it("alerte sens enroulement : bandeau rouge bloquant en tête avec les 3 options", () => {
    const { container } = render(
      <ResultatControle
        result={buildResult({
          score_conformite: 30,
          decision_recommandee: "rejeter",
          sens_enroulement_demande: "SE3",
          sens_enroulement_detecte: "SE7",
          alerte_sens_enroulement: {
            message: "Le sens vu sur la photo ne correspond pas au demandé.",
            options_correction: [
              {
                code: "inversion_cliche",
                libelle: "Inverser le cliché",
                description: "Re-monter la plaque dans l'autre sens.",
              },
              {
                code: "ajustement_rebobineuse",
                libelle: "Ajuster la rebobineuse",
                description: "Inverser la sortie de la rebobineuse.",
              },
              {
                code: "confirmation_client",
                libelle: "Confirmation client",
                description: "Appeler le client pour valider le sens livré.",
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

  it("résultat minimal (champs Lot C uniquement) : pas de crash, sections optionnelles absentes", () => {
    render(<ResultatControle result={buildResult()} />);
    // ecarts undefined → bloc rendu mais "0 écart"
    expect(screen.getByTestId("ecarts-block")).toBeInTheDocument();
    // Sections optionnelles absentes
    expect(screen.queryByTestId("score-decision")).toBeNull();
    expect(screen.queryByTestId("sens-sortie")).toBeNull();
    expect(screen.queryByTestId("alerte-sens-enroulement")).toBeNull();
    expect(screen.queryByTestId("conformes-block")).toBeNull();
    expect(screen.queryByTestId("manquants-block")).toBeNull();
    expect(screen.queryByTestId("confiance-limites")).toBeNull();
  });
});
