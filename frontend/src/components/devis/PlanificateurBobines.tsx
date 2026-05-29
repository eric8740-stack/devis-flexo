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
  type DecisionSurplus,
  type ImposeType,
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
  // Mode IMPOSE actif : "aucun" (par défaut, scénarios A/B/C seuls) ou 1
  // des 3 modes mutuellement exclusifs. Restauré au reload selon
  // `initialSelection.impose_type`.
  const initialImposeMode: "aucun" | ImposeType =
    initialSelection?.impose_type ??
    (initialSelection?.scenario === "IMPOSE" ? "nb_etiq" : "aucun");
  const [imposeMode, setImposeMode] = useState<"aucun" | ImposeType>(
    initialImposeMode,
  );
  const [nbEtiqImposeInput, setNbEtiqImposeInput] = useState<string>(
    initialSelection?.scenario === "IMPOSE" &&
      initialSelection.impose_type === "nb_etiq"
      ? String(initialSelection.nb_bobine)
      : "",
  );
  const [nbBobinesImposeInput, setNbBobinesImposeInput] = useState<string>(
    initialSelection?.nb_bobines_demande !== undefined &&
      initialSelection?.nb_bobines_demande !== null
      ? String(initialSelection.nb_bobines_demande)
      : "",
  );
  const [packagingEtiqInput, setPackagingEtiqInput] = useState<string>(
    initialSelection?.impose_type === "packaging"
      ? String(initialSelection.nb_bobine)
      : "",
  );
  const [decisionSurplus, setDecisionSurplus] =
    useState<DecisionSurplus | null>(
      initialSelection?.decision_surplus ?? null,
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
    // Dispatch selon le mode IMPOSE actif. Mutex enforced côté backend
    // aussi (422 sinon), mais ici on garantit déjà la cohérence des
    // params envoyés.
    const nbEtiq = parseInt(nbEtiqImposeInput.trim(), 10);
    const nbBob = parseInt(nbBobinesImposeInput.trim(), 10);
    const packEtiq = parseInt(packagingEtiqInput.trim(), 10);
    const req: PlanificateurBobinesRequest = {
      quantite_commandee: quantiteCommandee,
      n_laize: nLaize,
      pas_mm: pasMm,
      mandrin_mm: mandrinMm,
      diametre_max_bobine_mm: diametreMaxBobineMm!,
      epaisseur_matiere_um: epaisseurMatiereUm!,
      nb_etiq_impose:
        imposeMode === "nb_etiq" && Number.isFinite(nbEtiq) && nbEtiq > 0
          ? nbEtiq
          : null,
      nb_bobines_impose:
        (imposeMode === "nb_bobines" || imposeMode === "packaging") &&
        Number.isFinite(nbBob) &&
        nbBob > 0
          ? nbBob
          : null,
      packaging_nb_etiq_par_bobine:
        imposeMode === "packaging" &&
        Number.isFinite(packEtiq) &&
        packEtiq > 0
          ? packEtiq
          : null,
    };
    const handle = setTimeout(() => {
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
    imposeMode,
    nbEtiqImposeInput,
    nbBobinesImposeInput,
    packagingEtiqInput,
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
    // q_ajustee selon le mode :
    //   - C_inf / C_sup : valeur native du scénario.
    //   - IMPOSE nb_bobines/packaging avec décision surplus : Q dérivée.
    //   - sinon : null (pas de modification de la Q du devis).
    let qAjusteePersist: number | null = scenario.q_ajustee ?? null;
    let imposeTypePersist = scenario.cle === "IMPOSE" ? imposeMode : null;
    if (imposeTypePersist === "aucun") imposeTypePersist = null;
    let decisionPersist: DecisionSurplus | null = null;
    if (
      scenario.cle === "IMPOSE" &&
      (imposeMode === "nb_bobines" || imposeMode === "packaging") &&
      decisionSurplus !== null
    ) {
      decisionPersist = decisionSurplus;
      if (decisionSurplus === "facture") {
        qAjusteePersist = scenario.q_si_facture ?? null;
      } else if (decisionSurplus === "stock") {
        qAjusteePersist = scenario.q_si_stock ?? null;
      } else if (decisionSurplus === "reduire") {
        qAjusteePersist = scenario.q_si_reduire ?? null;
      }
    }
    const body: PlanBobinesSelectionIn = {
      scenario: scenario.cle,
      nb_bobine: scenario.repartition[0]?.nb_etiq_par_bobine ?? 0,
      nb_bobines_total: scenario.nb_bobines_total,
      politique_reliquat: POLITIQUE_PAR_SCENARIO[scenario.cle],
      q_ajustee: qAjusteePersist,
      force_diametre: forcer ? true : null,
      motif_forcage: forcer ? motif : null,
      impose_type: imposeTypePersist,
      nb_bobines_demande: scenario.nb_bobines_demande ?? null,
      surplus_bobines: scenario.surplus_bobines ?? null,
      decision_surplus: decisionPersist,
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
      <header className="space-y-2">
        <div>
          <h4 className="text-sm font-semibold">Plan de bobines</h4>
          <p className="text-xs text-muted-foreground">
            Interne · {result ? `nb max physique : ${result.nb_max_par_bobine} étiq` : ""}
          </p>
        </div>
        {/* 3 modes IMPOSE mutuellement exclusifs (un seul à la fois).
            Le commerciale choisit le mode selon la contrainte client :
              - aucun (par défaut) : scénarios A/B/C seuls
              - nb_etiq : « 1500 étiq/bobine »
              - nb_bobines : « 40 bobines »
              - packaging : « 40 bobines × 1000 étiq » (les 2)
            Le backend rejette en 422 si plusieurs modes simultanés. */}
        <div
          role="radiogroup"
          aria-label="Mode imposé client"
          data-testid="plan-bobines-mode-selector"
          className="flex flex-wrap gap-2 text-xs"
        >
          {(
            [
              ["aucun", "Aucun"],
              ["nb_etiq", "Nb/bobine"],
              ["nb_bobines", "Nb bobines"],
              ["packaging", "Packaging (N × X)"],
            ] as const
          ).map(([mode, label]) => {
            const active = imposeMode === mode;
            return (
              <button
                key={mode}
                type="button"
                role="radio"
                aria-checked={active}
                data-testid={`plan-bobines-mode-${mode}`}
                onClick={() => setImposeMode(mode)}
                className={
                  "rounded-full border px-3 py-1 transition " +
                  (active
                    ? "border-blue-600 bg-blue-50 font-medium text-blue-900"
                    : "border-border bg-background text-muted-foreground hover:bg-muted/40")
                }
              >
                {label}
              </button>
            );
          })}
        </div>
        {imposeMode !== "aucun" && (
          <div className="flex flex-wrap items-end gap-3">
            {imposeMode === "nb_etiq" && (
              <div className="flex flex-col gap-1">
                <Label
                  htmlFor="plan-bobines-nb-etiq"
                  className="text-xs text-muted-foreground"
                >
                  Nb étiquettes / bobine
                </Label>
                <Input
                  id="plan-bobines-nb-etiq"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  placeholder="ex : 1500"
                  className="h-8 w-32 text-sm"
                  value={nbEtiqImposeInput}
                  onChange={(e) => setNbEtiqImposeInput(e.target.value)}
                />
              </div>
            )}
            {(imposeMode === "nb_bobines" || imposeMode === "packaging") && (
              <div className="flex flex-col gap-1">
                <Label
                  htmlFor="plan-bobines-nb-bobines"
                  className="text-xs text-muted-foreground"
                >
                  Nb bobines
                </Label>
                <Input
                  id="plan-bobines-nb-bobines"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  placeholder="ex : 40"
                  className="h-8 w-32 text-sm"
                  value={nbBobinesImposeInput}
                  onChange={(e) => setNbBobinesImposeInput(e.target.value)}
                />
              </div>
            )}
            {imposeMode === "packaging" && (
              <div className="flex flex-col gap-1">
                <Label
                  htmlFor="plan-bobines-pack-etiq"
                  className="text-xs text-muted-foreground"
                >
                  Étiquettes / bobine
                </Label>
                <Input
                  id="plan-bobines-pack-etiq"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  placeholder="ex : 1000"
                  className="h-8 w-32 text-sm"
                  value={packagingEtiqInput}
                  onChange={(e) => setPackagingEtiqInput(e.target.value)}
                />
              </div>
            )}
          </div>
        )}
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
            // Décision surplus (IMPOSE nb_bobines/packaging uniquement). La
            // décision pilote la Q persistée (facture=production, stock=
            // demande, reduire=multiple inférieur de n_laize sous demande).
            decisionSurplus={
              sc.cle === "IMPOSE" &&
              (imposeMode === "nb_bobines" || imposeMode === "packaging")
                ? decisionSurplus
                : null
            }
            onChangeDecisionSurplus={setDecisionSurplus}
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
  decisionSurplus,
  onChangeDecisionSurplus,
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
  decisionSurplus: DecisionSurplus | null;
  onChangeDecisionSurplus: (d: DecisionSurplus) => void;
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

      {/* Bloc surplus : visible UNIQUEMENT pour IMPOSE nb_bobines / packaging
          quand l'opérateur a demandé un nb précis. Affiche le delta entre
          la production réelle (sortie machine, multiple n_laize) et la
          demande client, plus les 3 options de décision sur ce surplus. */}
      {scenario.cle === "IMPOSE" &&
        scenario.nb_bobines_demande !== null &&
        scenario.nb_bobines_demande !== undefined && (
          <div
            data-testid="plan-bobines-surplus-block"
            className="mt-2 space-y-1.5 rounded border border-amber-300 bg-amber-50/60 p-2 text-xs"
          >
            <p>
              <span className="text-muted-foreground">Demandé :</span>{" "}
              <strong>{scenario.nb_bobines_demande}</strong> bobines
              {" · "}
              <span className="text-muted-foreground">Produit :</span>{" "}
              <strong>{scenario.nb_bobines_total}</strong> bobines
              {" · "}
              <span className="text-muted-foreground">Surplus :</span>{" "}
              <strong>{scenario.surplus_bobines ?? 0}</strong> bobines /{" "}
              <strong>{scenario.surplus_etiq ?? 0}</strong> étiq
            </p>
            {(scenario.surplus_bobines ?? 0) > 0 && (
              <div className="space-y-1">
                <p className="text-muted-foreground">
                  Décision sur le surplus :
                </p>
                <div
                  role="radiogroup"
                  aria-label="Décision sur le surplus"
                  data-testid="plan-bobines-decision-surplus"
                  className="flex flex-wrap gap-1.5"
                >
                  {(
                    [
                      [
                        "facture",
                        `Facturer (${scenario.q_si_facture ?? "—"})`,
                      ],
                      [
                        "stock",
                        `Stock (${scenario.q_si_stock ?? "—"})`,
                      ],
                      [
                        "reduire",
                        `Réduire (${scenario.q_si_reduire ?? "—"})`,
                      ],
                    ] as const
                  ).map(([decision, label]) => {
                    const active = decisionSurplus === decision;
                    return (
                      <button
                        key={decision}
                        type="button"
                        role="radio"
                        aria-checked={active}
                        data-testid={`plan-bobines-decision-${decision}`}
                        onClick={() => onChangeDecisionSurplus(decision)}
                        className={
                          "rounded border px-2 py-1 transition " +
                          (active
                            ? "border-blue-600 bg-blue-50 font-medium text-blue-900"
                            : "border-border bg-white text-foreground hover:bg-muted/40")
                        }
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

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
