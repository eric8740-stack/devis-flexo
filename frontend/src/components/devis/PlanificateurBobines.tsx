"use client";

/**
 * Plan de bobines — bloc interactif INTERNE (commercial uniquement)
 * dans le rapport de fabrication sur `/devis/[id]`.
 *
 * Affiche 3 scénarios (+ optionnellement IMPOSE) de découpe en bobines,
 * avec coût rebobinage en LECTURE SEULE du moteur existant.
 *
 * Finition (cette PR) :
 *  - Persistance : sélection sauvegardée dans `payload_input.plan_bobines`
 *    via PUT ciblé (merge partiel server-side, autres clés préservées).
 *  - Restauration : si `initialSelection` fourni (au reload du devis),
 *    la carte sélectionnée est restaurée.
 *  - Scénario C : bouton « Appliquer cette quantité » → navigation vers
 *    `/optimisation?devis_id=X&q=Y` (le hydrater lit le param `q`).
 *  - IMPOSE physiquement impossible : bouton « Forcer malgré tout » qui
 *    réclame un motif non vide AVANT enregistrement. Souveraineté
 *    préservée + traçabilité (force_diametre + motif_forcage stockés).
 */
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  planifierBobines,
  sauvegarderPlanBobines,
  type PlanBobinesSelectionIn,
  type PlanificateurBobinesRequest,
  type PlanificateurBobinesResponse,
  type PolitiqueReliquat,
  type ScenarioBobinesKey,
  type ScenarioBobinesOut,
} from "@/lib/api";

interface Props {
  /** ID du devis pour la persistance ciblée. */
  devisId: number;
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
  /**
   * Sélection antérieure restaurée depuis `payload_input.plan_bobines`
   * (le devis a déjà été enregistré une fois). null = pas de choix encore.
   */
  initialSelection?: PlanBobinesSelectionIn | null;
}

const COULEURS_CLE: Record<ScenarioBobinesKey, string> = {
  A: "border-l-blue-600 bg-blue-50/40",
  B: "border-l-emerald-600 bg-emerald-50/40",
  C_inf: "border-l-amber-500 bg-amber-50/40",
  C_sup: "border-l-amber-600 bg-amber-50/60",
  IMPOSE: "border-l-purple-600 bg-purple-50/40",
};

const POLITIQUE_PAR_SCENARIO: Record<ScenarioBobinesKey, PolitiqueReliquat> = {
  A: "pleines_plus_reliquat",
  B: "equilibrees",
  C_inf: "tomber_juste",
  C_sup: "tomber_juste",
  IMPOSE: "pleines_plus_reliquat",
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
  devisId,
  quantiteCommandee,
  nLaize,
  pasMm,
  mandrinMm,
  diametreMaxBobineMm,
  epaisseurMatiereUm,
  initialSelection = null,
}: Props) {
  const router = useRouter();
  const { toast } = useToast();
  const [nbImposeInput, setNbImposeInput] = useState<string>(
    initialSelection?.scenario === "IMPOSE"
      ? String(initialSelection.nb_bobine)
      : "",
  );
  const [result, setResult] = useState<PlanificateurBobinesResponse | null>(
    null,
  );
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState<boolean>(false);
  const [scenarioChoisi, setScenarioChoisi] =
    useState<ScenarioBobinesKey | null>(
      initialSelection?.scenario ?? null,
    );
  // Workflow forçage IMPOSE : motif textarea + bouton « Forcer ».
  const [motifForcage, setMotifForcage] = useState<string>(
    initialSelection?.motif_forcage ?? "",
  );
  const [forcageActif, setForcageActif] = useState<boolean>(
    initialSelection?.force_diametre === true,
  );
  const [persisting, setPersisting] = useState<boolean>(false);

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

  // Helper persistance : appelle le PUT ciblé. Pour IMPOSE forçage, le motif
  // doit être non vide (vérification frontale + back-end revérifie 422).
  const persisterChoix = (
    scenario: ScenarioBobinesOut,
    forcer: boolean,
  ): void => {
    if (persisting) return;
    const motif = motifForcage.trim();
    if (forcer && !motif) {
      toast({
        title: "Motif obligatoire",
        description:
          "Pour forcer un scénario physiquement infaisable, renseigne un motif (audit/traçabilité).",
        variant: "destructive",
      });
      return;
    }
    const body: PlanBobinesSelectionIn = {
      scenario: scenario.cle,
      nb_bobine: scenario.repartition[0]?.nb_etiq_par_bobine ?? 0,
      nb_bobines_total: scenario.nb_bobines_total,
      politique_reliquat: POLITIQUE_PAR_SCENARIO[scenario.cle],
      q_ajustee: scenario.q_ajustee,
      force_diametre: forcer ? true : null,
      motif_forcage: forcer ? motif : null,
    };
    setPersisting(true);
    sauvegarderPlanBobines(devisId, body)
      .then(() => {
        setScenarioChoisi(scenario.cle);
        setForcageActif(forcer);
        toast({
          title: forcer ? "Forçage enregistré ⚠" : "Choix enregistré ✓",
          description: forcer
            ? `Scénario ${scenario.cle} retenu malgré l'impossibilité physique — motif tracé.`
            : `Scénario ${scenario.cle} sauvegardé sur le devis.`,
        });
      })
      .catch((err) => {
        toast({
          title: "Sauvegarde impossible",
          description: err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      })
      .finally(() => setPersisting(false));
  };

  const appliquerQAjustee = (qAjustee: number) => {
    router.push(`/optimisation?devis_id=${devisId}&q=${qAjustee}`);
  };

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

  const imposeImpossible = !!result?.alerte_impose?.physiquement_impossible;

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
            Revenir au client avec ces 2 chiffres avant chiffrage. Pour retenir
            ce scénario malgré l&apos;impossibilité, renseigne un motif et clique
            « Forcer malgré tout » sur la carte IMPOSE.
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
            estImpossible={sc.cle === "IMPOSE" ? imposeImpossible : false}
            forcageActif={forcageActif && scenarioChoisi === sc.cle}
            motifForcage={motifForcage}
            onChangeMotif={setMotifForcage}
            persisting={persisting}
            onChoisir={() => persisterChoix(sc, false)}
            onForcer={() => persisterChoix(sc, true)}
            onAppliquerQ={
              sc.q_ajustee !== null
                ? () => appliquerQAjustee(sc.q_ajustee!)
                : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}

function ScenarioCard({
  scenario,
  quantiteCommandee,
  estRecommande,
  estChoisi,
  estImpossible,
  forcageActif,
  motifForcage,
  onChangeMotif,
  persisting,
  onChoisir,
  onForcer,
  onAppliquerQ,
}: {
  scenario: ScenarioBobinesOut;
  quantiteCommandee: number;
  estRecommande: boolean;
  estChoisi: boolean;
  estImpossible: boolean;
  forcageActif: boolean;
  motifForcage: string;
  onChangeMotif: (v: string) => void;
  persisting: boolean;
  onChoisir: () => void;
  onForcer: () => void;
  onAppliquerQ?: () => void;
}) {
  const couleur = COULEURS_CLE[scenario.cle];
  const estC = scenario.cle === "C_inf" || scenario.cle === "C_sup";
  const estImposeCarte = scenario.cle === "IMPOSE";
  return (
    <div
      data-testid={`plan-bobines-card-${scenario.cle}`}
      className={
        "rounded-md border border-border border-l-4 px-3 py-2 text-sm " +
        couleur +
        (estChoisi ? " ring-2 ring-blue-500" : "") +
        (estImpossible && !forcageActif ? " opacity-70" : "")
      }
    >
      <div className="flex items-baseline justify-between gap-2">
        <p className="font-semibold">{scenario.titre}</p>
        <div className="flex items-center gap-1">
          {estRecommande && (
            <span
              data-testid={`plan-bobines-badge-recommande-${scenario.cle}`}
              className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900"
            >
              ⭐ recommandé
            </span>
          )}
          {estImpossible && !forcageActif && (
            <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-900">
              impossible
            </span>
          )}
          {forcageActif && estChoisi && (
            <span
              data-testid={`plan-bobines-badge-force-${scenario.cle}`}
              className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-900"
            >
              ⚠ forcé
            </span>
          )}
        </div>
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

      {/* Forçage IMPOSE : motif obligatoire (anti-fléau, traçabilité). */}
      {estImposeCarte && estImpossible && (
        <div
          data-testid="plan-bobines-motif-block"
          className="mt-2 space-y-1 rounded border border-red-300 bg-white/70 p-2"
        >
          <Label
            htmlFor={`motif-${scenario.cle}`}
            className="text-xs text-red-900"
          >
            Motif de forçage (obligatoire pour retenir ce scénario)
          </Label>
          <textarea
            id={`motif-${scenario.cle}`}
            data-testid="plan-bobines-motif-input"
            className="w-full rounded border border-input bg-white px-2 py-1 text-xs"
            rows={2}
            placeholder="ex : client accepte les sous-bobines en sortie atelier."
            value={motifForcage}
            onChange={(e) => onChangeMotif(e.target.value)}
          />
        </div>
      )}

      <div className="mt-2 flex flex-wrap gap-2">
        {estC && onAppliquerQ !== undefined && (
          <Button
            variant="outline"
            size="sm"
            onClick={onAppliquerQ}
            data-testid={`plan-bobines-btn-q-${scenario.cle}`}
            className="h-7 text-xs"
          >
            Appliquer cette quantité ({scenario.q_ajustee})
          </Button>
        )}
        {estImposeCarte && estImpossible ? (
          <Button
            variant="outline"
            size="sm"
            onClick={onForcer}
            disabled={persisting || motifForcage.trim().length === 0}
            data-testid={`plan-bobines-btn-forcer-${scenario.cle}`}
            className="h-7 text-xs text-red-900 hover:bg-red-50"
          >
            Forcer malgré tout
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={onChoisir}
            disabled={persisting}
            data-testid={`plan-bobines-btn-${scenario.cle}`}
            className="h-7 text-xs"
          >
            {estChoisi ? "✓ Sélectionné" : "Choisir"}
          </Button>
        )}
      </div>
    </div>
  );
}
