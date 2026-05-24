"use client";

import { cn } from "@/lib/utils";
import type {
  ControleBatResult,
  DecisionRecommandee,
} from "@/lib/api/controleBat";

interface TentativesTimelineProps {
  attempts: ControleBatResult[];
  // Index dans `attempts` du résultat actuellement affiché en plein écran
  // (en général le dernier). Permet de mettre en évidence la tentative
  // sélectionnée sans changer l'ordre du tableau.
  currentIndex: number;
}

/**
 * Sprint 15 Lot E — Frise horizontale des tentatives successives.
 *
 * Compact, sticky en haut du résultat. Une pastille par tentative avec
 * le numéro, le score (ou « ? » si non disponible) et un ton couleur
 * dérivé de la décision_recommandee de cette tentative-là.
 *
 * Pas de navigation entre tentatives pour le Lot E — la sélection
 * "regarder une tentative précédente" relèvera d'une évolution future
 * si besoin. Le but est de donner à l'opérateur un repère visuel sur
 * sa progression face à un BAT difficile.
 */
export function TentativesTimeline({
  attempts,
  currentIndex,
}: TentativesTimelineProps) {
  if (attempts.length === 0) return null;
  return (
    <div
      data-testid="tentatives-timeline"
      aria-label="Séquence des tentatives"
      className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-muted/30 p-3"
    >
      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Tentatives
      </span>
      {attempts.map((a, i) => (
        <TentativeChip
          key={a.controle_id}
          attempt={a}
          isCurrent={i === currentIndex}
        />
      ))}
    </div>
  );
}

function TentativeChip({
  attempt,
  isCurrent,
}: {
  attempt: ControleBatResult;
  isCurrent: boolean;
}) {
  const tone = decisionTone(attempt.decision_recommandee);
  const scoreLabel =
    attempt.score_conformite === undefined
      ? "—"
      : `${Math.round(attempt.score_conformite)}%`;
  return (
    <div
      data-testid={`tentative-chip-${attempt.tentative}`}
      aria-current={isCurrent ? "step" : undefined}
      className={cn(
        "flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
        tone,
        isCurrent && "ring-2 ring-foreground/40",
      )}
    >
      <span className="font-semibold">#{attempt.tentative}</span>
      <span className="font-mono text-xs">{scoreLabel}</span>
    </div>
  );
}

function decisionTone(decision: DecisionRecommandee | undefined): string {
  if (decision === "valider")
    return "bg-emerald-100 text-emerald-900 border-emerald-300";
  if (decision === "ajuster")
    return "bg-amber-100 text-amber-900 border-amber-300";
  if (decision === "rejeter")
    return "bg-red-100 text-red-900 border-red-300";
  return "bg-gray-100 text-gray-800 border-gray-300";
}
