"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  AlerteSensEnroulement,
  ControleBatResult,
  DecisionRecommandee,
  EcartDetail,
  GraviteEcart,
  NiveauConfiance,
} from "@/lib/api/controleBat";

interface ResultatControleProps {
  result: ControleBatResult;
}

/**
 * Sprint 15 Lot D — Rendu détaillé d'un résultat de Contrôle BAT IA.
 *
 * Lecture opérateur, tactile. L'ordre des sections est volontairement
 * orienté décision :
 *   1. Alerte sens enroulement (BLOQUANTE → en tête si présente).
 *   2. Score + décision recommandée (résumé visuel immédiat).
 *   3. Sens de sortie (détecté vs demandé) même hors alerte.
 *   4. Écarts (triés critique > majeur > mineur, couleur par gravité).
 *   5. Éléments conformes / manquants (checklist rapide).
 *   6. Niveau de confiance + limites d'analyse (transparence IA).
 *
 * Aucune action ici — les boutons valider/ajuster/recommencer relèvent
 * du Lot E (workflow re-tirage + décision).
 */
export function ResultatControle({ result }: ResultatControleProps) {
  const ecartsTries = trierEcarts(result.ecarts);
  // score_conformite est sérialisé Decimal → string par Pydantic v2 (pattern
  // projet, cf. matcher-outil). Parsing UNIQUEMENT à l'affichage.
  const scoreNum =
    result.score_conformite !== null
      ? parseFloat(result.score_conformite)
      : null;

  return (
    <section
      data-testid="resultat-controle"
      aria-label="Résultat du contrôle BAT"
      className="space-y-4"
    >
      <header className="text-sm text-muted-foreground">
        Contrôle #{result.controle_id} · tentative {result.tentative}
      </header>

      {result.alerte_sens_enroulement && (
        <AlerteSensEnroulementBlock
          alerte={result.alerte_sens_enroulement}
          sensDetecte={result.sens_enroulement_detecte}
          sensDemande={result.sens_enroulement_demande}
        />
      )}

      <ScoreEtDecisionBlock
        score={scoreNum}
        decision={result.decision_recommandee}
      />

      {!result.alerte_sens_enroulement && (
        <SensSortieBlock
          sensDetecte={result.sens_enroulement_detecte}
          sensDemande={result.sens_enroulement_demande}
        />
      )}

      <EcartsBlock ecarts={ecartsTries} />

      <ConformesManquantsBlock
        conformes={result.elements_conformes}
        manquants={result.elements_manquants}
      />

      <ConfianceEtLimitesBlock
        niveau={result.niveau_confiance}
        limites={result.limites_analyse}
      />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Score + décision
// ---------------------------------------------------------------------------

function ScoreEtDecisionBlock({
  score,
  decision,
}: {
  score: number | null;
  decision: DecisionRecommandee | null;
}) {
  if (score === null && !decision) return null;
  return (
    <Card data-testid="score-decision">
      <CardContent className="grid gap-4 p-4 sm:grid-cols-[auto_1fr] sm:items-center">
        {score !== null && <ScorePastille score={score} />}
        {decision && <DecisionBadge decision={decision} />}
      </CardContent>
    </Card>
  );
}

function ScorePastille({ score }: { score: number }) {
  // Seuils métier : ≥85 % vert, 60-84 % orange, <60 % rouge.
  // Alignés sur la logique decision_recommandee (valider/ajuster/rejeter).
  const tone =
    score >= 85
      ? "bg-emerald-100 text-emerald-900 ring-emerald-300"
      : score >= 60
        ? "bg-amber-100 text-amber-900 ring-amber-300"
        : "bg-red-100 text-red-900 ring-red-300";
  const scoreArrondi = Math.round(score);
  return (
    <div className="flex items-center gap-4">
      <div
        data-testid="score-pastille"
        className={cn(
          "flex h-24 w-24 flex-shrink-0 items-center justify-center rounded-full ring-4 sm:h-28 sm:w-28",
          tone,
        )}
      >
        <span className="text-3xl font-bold sm:text-4xl">{scoreArrondi}%</span>
      </div>
      <div>
        <div className="text-xs uppercase tracking-wide text-muted-foreground">
          Score de conformité
        </div>
        <JaugeScore score={score} />
      </div>
    </div>
  );
}

function JaugeScore({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const fill =
    score >= 85
      ? "bg-emerald-500"
      : score >= 60
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <div
      role="meter"
      aria-label="Jauge score de conformité"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      className="mt-1 h-3 w-40 overflow-hidden rounded-full bg-muted sm:w-56"
    >
      <div
        className={cn("h-full transition-all", fill)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function DecisionBadge({ decision }: { decision: DecisionRecommandee }) {
  // Aligné sur DecisionRecommandee backend (frozenset `valider`,
  // `ajuster_avant_demarrage`, `rejeter`).
  const config: Record<
    DecisionRecommandee,
    { libelle: string; tone: string; icone: string }
  > = {
    valider: {
      libelle: "Valider la production",
      tone: "bg-emerald-100 text-emerald-900 border-emerald-300",
      icone: "✅",
    },
    ajuster_avant_demarrage: {
      libelle: "Ajuster avant démarrage",
      tone: "bg-amber-100 text-amber-900 border-amber-300",
      icone: "🔁",
    },
    rejeter: {
      libelle: "Rejeter — non conforme",
      tone: "bg-red-100 text-red-900 border-red-300",
      icone: "⛔",
    },
  };
  const c = config[decision];
  return (
    <div
      data-testid={`decision-${decision}`}
      className={cn(
        "flex items-center gap-3 rounded-md border-2 p-3 sm:justify-self-end",
        c.tone,
      )}
    >
      <span aria-hidden="true" className="text-2xl">
        {c.icone}
      </span>
      <div>
        <div className="text-xs uppercase tracking-wide opacity-80">
          Décision recommandée
        </div>
        <div className="text-base font-semibold sm:text-lg">{c.libelle}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sens d'enroulement
// ---------------------------------------------------------------------------

function AlerteSensEnroulementBlock({
  alerte,
  sensDetecte,
  sensDemande,
}: {
  alerte: AlerteSensEnroulement;
  sensDetecte: string | null;
  sensDemande: string | null;
}) {
  return (
    <div
      role="alert"
      data-testid="alerte-sens-enroulement"
      className="space-y-3 rounded-md border-2 border-red-500 bg-red-50 p-4"
    >
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="text-2xl">
          ⚠️
        </span>
        <div className="flex-1">
          <div className="text-base font-bold text-red-900 sm:text-lg">
            Sens d&apos;enroulement incohérent — production bloquée
          </div>
          <p className="mt-1 text-sm text-red-900">{alerte.message}</p>
          <p className="mt-1 text-sm text-red-900">
            Demandé : <strong>{sensDemande ?? "—"}</strong> · Détecté :{" "}
            <strong>{sensDetecte ?? "—"}</strong>
          </p>
        </div>
      </div>
      <div className="space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-red-900">
          Options de correction
        </div>
        <ul className="space-y-2">
          {alerte.options_correction.map((opt) => (
            <li
              key={opt.code}
              data-testid={`option-correction-${opt.code}`}
              className={cn(
                "rounded-md border p-3",
                // Sprint 15 Lot 4 backend — `recommandee=true` sur l'option
                // auto-sélectionnée par le diagnostic coherence_sens. Le
                // backend place déjà cette option en premier ; on la met
                // visuellement en avant (encadré coloré + badge).
                opt.recommandee
                  ? "border-red-500 bg-red-100"
                  : "border-red-300 bg-white",
              )}
            >
              <div className="flex items-baseline justify-between gap-2">
                <div className="text-sm font-semibold text-red-900">
                  {opt.libelle}
                </div>
                {opt.recommandee && (
                  <span
                    data-testid={`option-recommandee-${opt.code}`}
                    className="rounded bg-red-600 px-2 py-0.5 text-xs font-semibold text-white"
                  >
                    Recommandée
                  </span>
                )}
              </div>
              <div className="text-sm text-red-900/80">{opt.description}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function SensSortieBlock({
  sensDetecte,
  sensDemande,
}: {
  sensDetecte: string | null;
  sensDemande: string | null;
}) {
  if (!sensDetecte && !sensDemande) return null;
  const coherent =
    sensDetecte !== null &&
    sensDemande !== null &&
    sensDetecte === sensDemande;
  return (
    <Card data-testid="sens-sortie">
      <CardHeader>
        <CardTitle className="text-base">Sens d&apos;enroulement</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <KeyValue label="Demandé" value={sensDemande ?? "—"} />
        <KeyValue
          label="Détecté"
          value={sensDetecte ?? "—"}
          highlight={
            coherent
              ? "bg-emerald-100 text-emerald-900"
              : sensDetecte
                ? "bg-amber-100 text-amber-900"
                : undefined
          }
        />
      </CardContent>
    </Card>
  );
}

function KeyValue({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: string;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "mt-1 inline-block rounded px-2 py-1 font-mono text-base font-semibold",
          highlight ?? "text-foreground",
        )}
      >
        {value}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Écarts
// ---------------------------------------------------------------------------

const ORDRE_GRAVITE: Record<string, number> = {
  critique: 0,
  majeur: 1,
  mineur: 2,
};

function trierEcarts(ecarts: EcartDetail[]): EcartDetail[] {
  // Tri stable par gravité (critique d'abord) — `Array.sort` est stable
  // depuis ES2019 donc l'ordre intra-gravité reste celui du backend. Les
  // gravités inconnues (le backend laisse passer en str pour rester souple
  // si l'IA ajoute une nuance vocabulaire) tombent en fin de liste.
  return [...ecarts].sort(
    (a, b) =>
      (ORDRE_GRAVITE[a.gravite] ?? 99) - (ORDRE_GRAVITE[b.gravite] ?? 99),
  );
}

function EcartsBlock({ ecarts }: { ecarts: EcartDetail[] }) {
  if (ecarts.length === 0) {
    return (
      <Card data-testid="ecarts-block">
        <CardHeader>
          <CardTitle className="text-base">
            Écarts détectés (0)
          </CardTitle>
          <CardDescription>Aucun écart détecté par l&apos;IA.</CardDescription>
        </CardHeader>
      </Card>
    );
  }
  return (
    <Card data-testid="ecarts-block">
      <CardHeader>
        <CardTitle className="text-base">
          Écarts détectés ({ecarts.length})
        </CardTitle>
        <CardDescription>
          Triés par gravité décroissante. Critiques en premier.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {ecarts.map((e, i) => (
          <EcartCard key={i} ecart={e} />
        ))}
      </CardContent>
    </Card>
  );
}

const ECART_DEFAULT_CONFIG = {
  libelle: "Écart",
  tone: "bg-gray-100 text-gray-900",
  border: "border-gray-400",
} as const;

const ECART_CONFIG: Record<
  GraviteEcart,
  { libelle: string; tone: string; border: string }
> = {
  critique: {
    libelle: "Critique",
    tone: "bg-red-100 text-red-900",
    border: "border-red-400",
  },
  majeur: {
    libelle: "Majeur",
    tone: "bg-amber-100 text-amber-900",
    border: "border-amber-400",
  },
  mineur: {
    libelle: "Mineur",
    tone: "bg-yellow-50 text-yellow-900",
    border: "border-yellow-300",
  },
};

function EcartCard({ ecart }: { ecart: EcartDetail }) {
  // Gravité backend = str libre (cf. EcartDetail extra="allow") ; bucket
  // par défaut pour toute valeur non-standard.
  const c = ECART_CONFIG[ecart.gravite as GraviteEcart] ?? ECART_DEFAULT_CONFIG;
  return (
    <div
      data-testid={`ecart-${ecart.gravite}`}
      className={cn("rounded-md border-l-4 p-3", c.border, c.tone)}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-wide">
          {c.libelle}
        </span>
        {ecart.localisation && (
          <span className="text-xs opacity-80">{ecart.localisation}</span>
        )}
      </div>
      {ecart.description && <p className="mt-1 text-sm">{ecart.description}</p>}
      {ecart.suggestion_correction && (
        <p className="mt-1 text-sm">
          <strong>Correction suggérée :</strong> {ecart.suggestion_correction}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Conformes / Manquants
// ---------------------------------------------------------------------------

function ConformesManquantsBlock({
  conformes,
  manquants,
}: {
  conformes: string[];
  manquants: string[];
}) {
  if (conformes.length === 0 && manquants.length === 0) return null;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card data-testid="conformes-block">
        <CardHeader>
          <CardTitle className="text-base text-emerald-900">
            ✓ Éléments conformes ({conformes.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {conformes.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {conformes.map((c, i) => (
                <li key={i}>• {c}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card data-testid="manquants-block">
        <CardHeader>
          <CardTitle className="text-base text-red-900">
            ✗ Éléments manquants ({manquants.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {manquants.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {manquants.map((m, i) => (
                <li key={i}>• {m}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Confiance + limites
// ---------------------------------------------------------------------------

function ConfianceEtLimitesBlock({
  niveau,
  limites,
}: {
  niveau: NiveauConfiance | null;
  limites: string[];
}) {
  if (!niveau && limites.length === 0) return null;
  const tone: Record<NiveauConfiance, string> = {
    haut: "bg-emerald-100 text-emerald-900",
    moyen: "bg-amber-100 text-amber-900",
    faible: "bg-red-100 text-red-900",
  };
  return (
    <Card data-testid="confiance-limites">
      <CardHeader>
        <div className="flex items-baseline justify-between gap-2">
          <CardTitle className="text-base">Confiance de l&apos;analyse</CardTitle>
          {niveau && (
            <span
              data-testid={`niveau-confiance-${niveau}`}
              className={cn(
                "rounded px-2 py-0.5 text-xs font-medium",
                tone[niveau],
              )}
            >
              Confiance : {niveau}
            </span>
          )}
        </div>
        <CardDescription>
          L&apos;analyse IA peut se tromper — un opérateur reste responsable
          de la décision finale.
        </CardDescription>
      </CardHeader>
      {limites.length > 0 && (
        <CardContent>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Limites identifiées
          </div>
          <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
            {limites.map((l, i) => (
              <li key={i}>• {l}</li>
            ))}
          </ul>
        </CardContent>
      )}
    </Card>
  );
}
