import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MotifForcageField } from "./MotifForcageField";

// Lot Souveraineté — le motif de forçage est RECOMMANDÉ, pas obligatoire.
// Un motif vide/court montre une PETITE NOTE DISCRÈTE (grise, non bloquante),
// jamais un encart d'erreur. Le submit n'est pas géré ici (pas de blocage).

describe("MotifForcageField — note discrète non bloquante", () => {
  it("motif vide → note discrète affichée (grise, pas un encart d'erreur)", () => {
    render(
      <MotifForcageField testIdPrefix="x" motif="" onChange={() => {}} />,
    );
    const note = screen.getByTestId("x-note");
    expect(note).toHaveTextContent(/note recommandée/i);
    // Discrète : classe grise muted, et SURTOUT pas un role=alert (encart rouge).
    expect(note.className).toMatch(/text-muted-foreground/);
    expect(note.className).not.toMatch(/destructive|text-red|bg-red/);
    expect(screen.queryByRole("alert")).toBeNull();
    // Placeholder harmonisé (recommandé, pas "obligatoire/minimum").
    expect(screen.getByTestId("x-motif")).toHaveAttribute(
      "placeholder",
      "Motif (recommandé — Règle 7)",
    );
  });

  it("motif court (< 10 car.) → note encore affichée", () => {
    render(
      <MotifForcageField testIdPrefix="x" motif="court" onChange={() => {}} />,
    );
    expect(screen.getByTestId("x-note")).toBeInTheDocument();
  });

  it("motif suffisant (>= 10 car.) → plus de note", () => {
    render(
      <MotifForcageField
        testIdPrefix="x"
        motif="Contrainte client export"
        onChange={() => {}}
      />,
    );
    expect(screen.queryByTestId("x-note")).toBeNull();
  });

  it("saisie → onChange propagé (pas de blocage)", async () => {
    const onChange = vi.fn();
    render(<MotifForcageField testIdPrefix="x" motif="" onChange={onChange} />);
    await userEvent.type(screen.getByTestId("x-motif"), "A");
    expect(onChange).toHaveBeenCalledWith("A");
  });
});
