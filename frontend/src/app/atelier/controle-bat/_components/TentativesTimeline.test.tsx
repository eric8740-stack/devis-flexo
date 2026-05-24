import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ControleBatResult } from "@/lib/api/controleBat";

import { TentativesTimeline } from "./TentativesTimeline";

// Sprint 15 Lot E — tests RTL de la timeline des tentatives.

function buildResult(
  overrides: Partial<ControleBatResult> = {},
): ControleBatResult {
  return {
    controle_id: 100,
    devis_id: 7,
    tentative: 1,
    ...overrides,
  };
}

describe("TentativesTimeline — Lot E", () => {
  it("attempts vide : pas de rendu (composant null)", () => {
    const { container } = render(
      <TentativesTimeline attempts={[]} currentIndex={-1} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("N chips rendus dans l'ordre du tableau, currentIndex marqué aria-current=step", () => {
    const attempts = [
      buildResult({
        controle_id: 100,
        tentative: 1,
        score_conformite: 45,
        decision_recommandee: "rejeter",
      }),
      buildResult({
        controle_id: 101,
        tentative: 2,
        score_conformite: 72,
        decision_recommandee: "ajuster",
      }),
      buildResult({
        controle_id: 102,
        tentative: 3,
        score_conformite: 91,
        decision_recommandee: "valider",
      }),
    ];
    render(
      <TentativesTimeline attempts={attempts} currentIndex={2} />,
    );
    const tl = screen.getByTestId("tentatives-timeline");
    const chips = within(tl).getAllByTestId(/^tentative-chip-/);
    expect(chips).toHaveLength(3);
    expect(chips[0]).toHaveTextContent("#1");
    expect(chips[0]).toHaveTextContent("45%");
    expect(chips[1]).toHaveTextContent("#2");
    expect(chips[2]).toHaveTextContent("#3");
    expect(chips[2]).toHaveAttribute("aria-current", "step");
    expect(chips[0]).not.toHaveAttribute("aria-current");
  });

  it("score absent : affiche un placeholder '—'", () => {
    render(
      <TentativesTimeline
        attempts={[
          buildResult({ controle_id: 100, tentative: 1 }),
        ]}
        currentIndex={0}
      />,
    );
    expect(
      screen.getByTestId("tentative-chip-1"),
    ).toHaveTextContent("—");
  });

  it("tons couleur selon decision_recommandee (valider/ajuster/rejeter)", () => {
    render(
      <TentativesTimeline
        attempts={[
          buildResult({
            controle_id: 100,
            tentative: 1,
            decision_recommandee: "valider",
          }),
          buildResult({
            controle_id: 101,
            tentative: 2,
            decision_recommandee: "ajuster",
          }),
          buildResult({
            controle_id: 102,
            tentative: 3,
            decision_recommandee: "rejeter",
          }),
        ]}
        currentIndex={2}
      />,
    );
    expect(
      screen.getByTestId("tentative-chip-1").className,
    ).toMatch(/emerald/);
    expect(
      screen.getByTestId("tentative-chip-2").className,
    ).toMatch(/amber/);
    expect(
      screen.getByTestId("tentative-chip-3").className,
    ).toMatch(/red/);
  });
});
