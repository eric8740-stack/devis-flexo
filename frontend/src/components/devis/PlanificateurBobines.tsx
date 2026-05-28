"use client";

/**
 * Plan de bobines — bloc interactif INTERNE (commercial uniquement)
 * dans le rapport de fabrication sur `/devis/[id]`.
 *
 * Affiche 3 scénarios (+ optionnellement IMPOSE) de découpe en bobines,
 * avec coût rebobinage en LECTURE SEULE du moteur existant. Le commercial
 * en choisit un. Le scénario C ajuste la quantité du devis → utilisateur
 * redirigé vers le flux existant « Modifie ce devis ».
 *
 * UX :
 *  - cartes color-codées, mobile-first
 *  - badge « ⭐ recommandé » sur le coût rebobinage le plus bas
 *  - alerte rouge si scénario IMPOSE physiquement impossible
 *  - aucun tooltip survol
 *
 * Calculs : zéro duplication — tout passe par `POST /api/devis/
 * planificateur-bobines` qui appelle `bat_calculs` (SSOT) + cost_engine
 * rebobinage (lecture seule).
 */
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  planifierBobines,
  type PlanificateurBobinesRequest,
  type PlanificateurBobinesResponse,
  type ScenarioBobinesKey,
  type ScenarioBobinesOut,
} from "@/lib/api";

interface Props {
  /** Quantité commandée du lot (étiquettes). */
  quantiteCommandee: number;
  /** Poses en laize (résultat optim). */
  nLaize: number;
  /** pas_mm = dev_étiq + écart_dev_réel (post-optim). */
  pasMm: number;
  mandrinMm: number;
  /**
   * Ø max accepté par la machine de pose du client (profil sprint 16).
   * null → planner non rendu (input manquant, voir brief « Étape 0 — Gate »).
   */
  diametreMaxBobineMm: number | null;
  /**
   * Épaisseur matière en µm. null → planner non rendu (gate inputs).
   */
  epaisseurMatiereUm: number | null;
}

const COULEURS_CLE: Record<ScenarioBobinesKey, string> = {
  A: "border-l-blue-600 bg-blue-50/40",
  B: "border-l-emerald-600 bg-emerald-50/40",
  C_inf: "border-l-amber-500 bg-amber-50/40",
  C_sup: "border-l-amber-600 bg-amber-50/60",
  IMPOSE: "border-l-purple-600 bg-purple-50/40",
};

function fmtEur(s: string | null): string {
  if (s === null) return "—";
  const n = parseFloat(s);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function PlanificateurBobines({
  quantiteCommandee,
  nLaize,
  pasMm,
  mandrinMm,
  diametreMaxBobineMm,
  epaisseurMatiereUm,
}: Props) {
  // Anti-fléau : input commercial pour le nb_etiq_impose client.
  const [nbImposeInput, setNbImposeInput] = useState<string>("");
  const [result, setResult] = useState<PlanificateurBobinesResponse | null>(
    null,
  );
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState<boolean>(false);
  const [scenarioChoisi, setScenarioChoisi] =
    useState<ScenarioBobinesKey | null>(null);

  const inputsManquants = useMemo<string[]>(() => {
    const missing: string[] = [];
    if (quantiteCommandee <= 0) missing.push("Q (quantité commandée)");
    if (nLaize <= 0) missing.push("n_laize (poses optim)");
    if (pasMm <= 0) missing.push("pas (dev + écart_dev réel)");
    if (mandrinMm <= 0) missing.push("mandrin");
    if (diametreMaxBobineMm === null || diametreMaxBobineMm <= 0)
      missing.push("Ø max bobine (profil client)");
    if (epaisseurMatiereUm === null || epaisseurMatiereUm <= 0)
      missing.push("épaisseur matière");
    return missing;
  }, [
    quantiteCommandee,
    nLaize,
    pasMm,
    mandrinMm,
    diametreMaxBobineMm,
    epaisseurMatiereUm,
  ]);

  // Recalcule à chaque évolution des inputs ou du nb_impose (debounce léger).
  useEffect(() => {
    if (inputsManquants.length > 0) {
      setResult(null);
      setErreur(null);
      return;
    }
    let cancelled = false;
    const nbImpose = nbImposeInput.trim()
      ? parseInt(nbImposeInput, 10)
      : null;
    const handle = setTimeout(() => {
      const req: PlanificateurBobinesRequest = {
        quantite_commandee: quantiteCommandee,
        n_laize: nLaize,
        pas_mm: pasMm,
        mandrin_mm: mandrinMm,
        diametre_max_bobine_mm: diametreMaxBobineMm!,
        epaisseur_matiere_um: epaisseurMatiereUm!,
        nb_etiq_impose: nbImpose && nbImpose > 0 ? nbImpose : null,
      };
      setChargement(true);
      planifierBobines(req)
        .then((res) => {
          if (!cancelled) {
            setResult(res);
            setErreur(null);
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setResult(null);
            setErreur(err instanceof Error ? err.message : "Erreur inconnue");
          }
        })
        .finally(() => {
          if (!cancelled) setChargement(false);
        });
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [
    quantiteCommandee,
    nLaize,
    pasMm,
    mandrinMm,
    diametreMaxBobineMm,
    epaisseurMatiereUm,
    nbImposeInput,
    inputsManquants.length,
  ]);

  // Gate Étape 0 du brief : « Si un input manque → le signaler, ne pas inventer ».
  if (inputsManquants.length > 0) {
    return (
      <div
        data-testid="plan-bobines-inputs-manquants"
        className="rounded-md border-l-4 border-l-muted-foreground/40 bg-muted/30 px-3 py-2 text-sm text-muted-foreground"
      >
        Plan de bobines indisponible — inputs manquants :{" "}
        {inputsManquants.join(", ")}.
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="plan-bobines">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold">Plan de bobines</h4>
          <p className="text-xs text-muted-foreground">
            Interne · {result ? `nb max physique : ${result.nb_max_par_bobine} étiq` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label
            htmlFor="plan-bobines-impose"
            className="text-xs text-muted-foreground"
          >
            Nb/bobine imposé client
          </Label>
          <Input
            id="plan-bobines-impose"
            type="number"
            inputMode="numeric"
            min={1}
            placeholder="optionnel"
            className="h-8 w-24 text-sm"
            value={nbImposeInput}
            onChange={(e) => setNbImposeInput(e.target.value)}
          />
        </div>
      </header>

      {/* Alerte anti-fléau : nb_impose > nb_max physique. */}
      {result?.alerte_impose?.physiquement_impossible && (
        <div
          role="alert"
          data-testid="plan-bobines-alerte-impose"
          className="rounded-md border-l-4 border-l-red-500 bg-red-50 px-3 py-2 text-sm text-red-900"
        >
          <p className="font-semibold">
            ⚠ {result.alerte_impose.nb_impose}/bobine physiquement impossible
            au Ø {diametreMaxBobineMm} mm
          </p>
          <p className="mt-1">
            Max réalisable à ce Ø : <strong>{result.alerte_impose.nb_realisable_max}</strong>{" "}
            étiq. Ø requis pour {result.alerte_impose.nb_impose} étiq :{" "}
            <strong>{result.alerte_impose.diametre_requis_mm} mm</strong>.
          </p>
          <p className="mt-1 text-xs text-red-700">
            Revenir au client avec ces 2 chiffres avant chiffrage. Forcer
            nécessite motif obligatoire (traçabilité).
          </p>
        </div>
      )}

      {chargement && (
        <p className="text-xs text-muted-foreground">Calcul…</p>
      )}
      {erreur && (
        <p className="text-xs text-red-700">Erreur : {erreur}</p>
      )}

      <div className="grid gap-2 sm:grid-cols-2">
        {(result?.scenarios ?? []).map((sc) => (
          <ScenarioCard
            key={sc.cle}
            scenario={sc}
            quantiteCommandee={quantiteCommandee}
            estRecommande={result?.recommande_cle === sc.cle}
            estChoisi={scenarioChoisi === sc.cle}
            estImpossible={
              sc.cle === "IMPOSE"
                ? !!result?.alerte_impose?.physiquement_impossible
                : false
            }
            onChoisir={() => setScenarioChoisi(sc.cle)}
          />
        ))}
      </div>

      {scenarioChoisi !== null && (
        <p
          data-testid="plan-bobines-choix"
          className="text-xs text-muted-foreground"
        >
          Scénario {scenarioChoisi} choisi.{" "}
          {scenarioChoisi.startsWith("C_") &&
            "→ Modifie ce devis pour appliquer la nouvelle quantité."}
        </p>
      )}
    </div>
  );
}

function ScenarioCard({
  scenario,
  quantiteCommandee,
  estRecommande,
  estChoisi,
  estImpossible,
  onChoisir,
}: {
  scenario: ScenarioBobinesOut;
  quantiteCommandee: number;
  estRecommande: boolean;
  estChoisi: boolean;
  estImpossible: boolean;
  onChoisir: () => void;
}) {
  const couleur = COULEURS_CLE[scenario.cle];
  return (
    <div
      data-testid={`plan-bobines-card-${scenario.cle}`}
      className={
        "rounded-md border border-border border-l-4 px-3 py-2 text-sm " +
        couleur +
        (estChoisi ? " ring-2 ring-blue-500" : "") +
        (estImpossible ? " opacity-70" : "")
      }
    >
      <div className="flex items-baseline justify-between gap-2">
        <p className="font-semibold">{scenario.titre}</p>
        {estRecommande && (
          <span
            data-testid={`plan-bobines-badge-recommande-${scenario.cle}`}
            className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900"
          >
            ⭐ recommandé
          </span>
        )}
        {estImpossible && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-900">
            impossible
          </span>
        )}
      </div>

      <ul className="mt-1 space-y-0.5 text-xs">
        <li>
          {scenario.nb_bobines_total} bobine{scenario.nb_bobines_total > 1 ? "s" : ""}{" "}
          ({scenario.nb_bobines_par_piste} × {scenario.repartition.length === 1
            ? `${scenario.repartition[0]!.nb_etiq_par_bobine} étiq`
            : "mix"})
        </li>
        {scenario.repartition.map((r, i) => (
          <li key={i} className="text-muted-foreground">
            {r.nb_bobines_par_piste} × {r.nb_etiq_par_bobine} étiq, Ø{" "}
            {r.diametre_mm} mm
          </li>
        ))}
        <li>
          Produit : <strong>{scenario.quantite_totale_etiq}</strong> étiq
          {" — "}
          {scenario.surprod_etiq >= 0
            ? `+${scenario.surprod_etiq} surprod`
            : `${scenario.surprod_etiq} (sous Q=${quantiteCommandee})`}
        </li>
        {scenario.cout_total_eur !== null && (
          <li>
            Coût rebobinage : <strong>{fmtEur(scenario.cout_total_eur)} €</strong>
            {scenario.mode_mandrins_optimal && (
              <span className="ml-1 text-muted-foreground">
                ({scenario.mode_mandrins_optimal === "pre_coupe"
                  ? "pré-coupé"
                  : "découpe interne"})
              </span>
            )}
          </li>
        )}
      </ul>

      <div className="mt-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onChoisir}
          data-testid={`plan-bobines-btn-${scenario.cle}`}
          className="h-7 text-xs"
        >
          {scenario.cle.startsWith("C_") ? "Ajuste Q" : "Choisir"}
        </Button>
      </div>
    </div>
  );
}
