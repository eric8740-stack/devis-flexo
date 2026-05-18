"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  getOnboardingCatalogueDefaults,
  getOnboardingStatus,
  postOnboardingInitialiser,
  type OnboardingCatalogueDefaults,
  type OnboardingMatiereDefault,
  type OnboardingOptionDefault,
} from "@/lib/api";

/**
 * Tunnel d'onboarding 4 écrans + 1 récap (Sprint 13 S13.C.3).
 *
 *   Étape 1 → Machines   (3 cards à cocher)
 *   Étape 2 → Cylindres  (19 chips à cocher)
 *   Étape 3 → Matières   (30 lignes regroupées par catégorie)
 *   Étape 4 → Options    (20 lignes regroupées par catégorie)
 *   Étape 5 → Récap + Valider → POST → toast → redirect /devis
 *
 * Convention "L'utilisateur DÉCOCHE ce qu'il n'a pas" : toutes les cases
 * démarrent cochées. Si l'utilisateur arrive ici avec un catalogue déjà
 * initialisé (status.catalogue_initialise=true), on lui propose d'aller
 * directement au dashboard plutôt que de tenter une 2e init (l'endpoint
 * back renverra 409 sinon).
 */

const TOTAL_STEPS = 4;

type Selection = {
  cylindres: Set<number>;
  machines: Set<string>;
  matieres: Set<string>;
  options: Set<string>;
};

function selectAllInitial(
  defaults: OnboardingCatalogueDefaults
): Selection {
  return {
    cylindres: new Set(defaults.cylindres_developpes_mm),
    machines: new Set(defaults.machines.map((m) => m.code)),
    matieres: new Set(defaults.matieres.map((m) => m.code)),
    options: new Set(defaults.options.map((o) => o.code)),
  };
}

function groupByCategorie<T extends { categorie?: string | null }>(
  items: T[]
): Record<string, T[]> {
  const out: Record<string, T[]> = {};
  for (const it of items) {
    const cat = it.categorie ?? "Autres";
    if (!out[cat]) out[cat] = [];
    out[cat].push(it);
  }
  return out;
}

export default function OnboardingPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [defaults, setDefaults] = useState<OnboardingCatalogueDefaults | null>(
    null
  );
  const [selection, setSelection] = useState<Selection | null>(null);
  const [step, setStep] = useState<number>(1);
  const [submitting, setSubmitting] = useState(false);
  const [alreadyInitialized, setAlreadyInitialized] = useState(false);
  const [loading, setLoading] = useState(true);

  // Chargement initial : catalogue + statut tenant en parallèle
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cat, st] = await Promise.all([
          getOnboardingCatalogueDefaults(),
          getOnboardingStatus(),
        ]);
        if (cancelled) return;
        setDefaults(cat);
        setSelection(selectAllInitial(cat));
        setAlreadyInitialized(st.catalogue_initialise);
      } catch (err) {
        toast({
          title: "Chargement impossible",
          description:
            err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [toast]);

  const matieresParCategorie = useMemo(
    () => (defaults ? groupByCategorie(defaults.matieres) : {}),
    [defaults]
  );
  const optionsParCategorie = useMemo(
    () => (defaults ? groupByCategorie(defaults.options) : {}),
    [defaults]
  );

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground">
        Chargement du catalogue…
      </div>
    );
  }

  if (alreadyInitialized) {
    return (
      <main className="mx-auto max-w-2xl p-6">
        <Card>
          <CardHeader>
            <CardTitle>Catalogue déjà initialisé</CardTitle>
            <CardDescription>
              Vous avez déjà finalisé l&apos;onboarding pour cette entreprise.
              Vous pouvez maintenant accéder à vos devis.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-end">
            <Button onClick={() => router.replace("/devis")}>
              Aller aux devis
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!defaults || !selection) {
    return null; // shouldn't happen — guard for TS
  }

  const toggleCyl = (mm: number) => {
    setSelection((s) => {
      if (!s) return s;
      const next = new Set(s.cylindres);
      if (next.has(mm)) next.delete(mm);
      else next.add(mm);
      return { ...s, cylindres: next };
    });
  };
  const toggleMachine = (code: string) => {
    setSelection((s) => {
      if (!s) return s;
      const next = new Set(s.machines);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return { ...s, machines: next };
    });
  };
  const toggleMatiere = (code: string) => {
    setSelection((s) => {
      if (!s) return s;
      const next = new Set(s.matieres);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return { ...s, matieres: next };
    });
  };
  const toggleOption = (code: string) => {
    setSelection((s) => {
      if (!s) return s;
      const next = new Set(s.options);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return { ...s, options: next };
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await postOnboardingInitialiser({
        cylindres_developpes_mm: Array.from(selection.cylindres),
        machines_codes: Array.from(selection.machines),
        matieres_codes: Array.from(selection.matieres),
        options_codes: Array.from(selection.options),
      });
      toast({
        title: "Catalogue initialisé",
        description: `${res.total} éléments créés dans votre catalogue.`,
      });
      router.replace("/devis");
    } catch (err) {
      toast({
        title: "Échec de l'onboarding",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <ProgressBar current={step} total={TOTAL_STEPS + 1} />

      {step === 1 && (
        <StepMachines
          defaults={defaults}
          selection={selection.machines}
          onToggle={toggleMachine}
        />
      )}
      {step === 2 && (
        <StepCylindres
          developpes={defaults.cylindres_developpes_mm}
          selection={selection.cylindres}
          onToggle={toggleCyl}
        />
      )}
      {step === 3 && (
        <StepMatieres
          groups={matieresParCategorie}
          selection={selection.matieres}
          onToggle={toggleMatiere}
        />
      )}
      {step === 4 && (
        <StepOptions
          groups={optionsParCategorie}
          selection={selection.options}
          onToggle={toggleOption}
        />
      )}
      {step === 5 && (
        <StepRecap defaults={defaults} selection={selection} />
      )}

      <div className="flex items-center justify-between gap-3 pt-2">
        <Button
          variant="outline"
          disabled={step === 1 || submitting}
          onClick={() => setStep((s) => Math.max(1, s - 1))}
        >
          ← Précédent
        </Button>
        <div className="text-sm text-muted-foreground">
          Étape {Math.min(step, TOTAL_STEPS)} / {TOTAL_STEPS}
          {step === TOTAL_STEPS + 1 && " — Récap"}
        </div>
        {step <= TOTAL_STEPS ? (
          <Button onClick={() => setStep((s) => s + 1)}>
            Suivant →
          </Button>
        ) : (
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Initialisation…" : "Valider et démarrer"}
          </Button>
        )}
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sous-composants
// ---------------------------------------------------------------------------

function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = Math.round((current / total) * 100);
  return (
    <div className="space-y-2">
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-foreground transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function CheckboxRow({
  id,
  checked,
  onChange,
  children,
}: {
  id: string;
  checked: boolean;
  onChange: () => void;
  children: React.ReactNode;
}) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3 transition-colors hover:bg-muted/50"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
      />
      <div className="flex-1">{children}</div>
    </label>
  );
}

function StepMachines({
  defaults,
  selection,
  onToggle,
}: {
  defaults: OnboardingCatalogueDefaults;
  selection: Set<string>;
  onToggle: (code: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Étape 1 — Quelles presses possédez-vous ?</CardTitle>
        <CardDescription>
          Cochez les machines présentes dans votre atelier. Vous pourrez en
          ajouter d&apos;autres ensuite, et surtout ajuster la{" "}
          <strong>vitesse pratique</strong> à votre cadence réelle.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {defaults.machines.map((m) => (
          <CheckboxRow
            key={m.code}
            id={`mach-${m.code}`}
            checked={selection.has(m.code)}
            onChange={() => onToggle(m.code)}
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <div className="font-medium">{m.nom}</div>
                <div className="text-xs text-muted-foreground">
                  {m.marque} • laize utile {m.laize_utile_mm} mm •{" "}
                  {m.nb_groupes_couleurs} groupes couleurs •{" "}
                  {m.nb_postes_decoupe} poste(s) découpe
                </div>
              </div>
              <div className="text-right text-xs">
                <div>
                  Vitesse pratique :{" "}
                  <strong>{m.vitesse_pratique_m_min} m/min</strong>
                </div>
                <div className="text-muted-foreground">
                  Catalogue {m.vitesse_nominale_constructeur_m_min} m/min
                </div>
              </div>
            </div>
            {m.notes && (
              <p className="mt-2 text-xs text-muted-foreground">{m.notes}</p>
            )}
          </CheckboxRow>
        ))}
      </CardContent>
    </Card>
  );
}

function StepCylindres({
  developpes,
  selection,
  onToggle,
}: {
  developpes: number[];
  selection: Set<number>;
  onToggle: (mm: number) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Étape 2 — Vos cylindres magnétiques</CardTitle>
        <CardDescription>
          19 développés standard du marché flexo. Décochez ceux que vous ne
          possédez pas — vous pourrez préciser l&apos;inventaire (poses par
          format PC) plus tard depuis vos paramètres.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {developpes.map((mm) => {
            const isOn = selection.has(mm);
            return (
              <button
                key={mm}
                type="button"
                onClick={() => onToggle(mm)}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                  isOn
                    ? "border-foreground bg-foreground text-background"
                    : "border-border text-muted-foreground hover:border-foreground/40"
                }`}
              >
                {mm} mm
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function StepMatieres({
  groups,
  selection,
  onToggle,
}: {
  groups: Record<string, OnboardingMatiereDefault[]>;
  selection: Set<string>;
  onToggle: (code: string) => void;
}) {
  const categoryOrder = ["papier", "film", "thermique", "synthetique", "special"];
  const orderedCats = categoryOrder.filter((c) => groups[c]);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Étape 3 — Vos matières</CardTitle>
        <CardDescription>
          30 matières du marché (papiers, films, thermiques, synthétiques,
          spéciaux). Décochez celles que vous ne travaillez pas — vous
          pourrez ajuster les prix au m² après.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {orderedCats.map((cat) => (
          <section key={cat}>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {cat}
            </h3>
            <div className="space-y-2">
              {groups[cat].map((m) => (
                <CheckboxRow
                  key={m.code}
                  id={`mat-${m.code}`}
                  checked={selection.has(m.code)}
                  onChange={() => onToggle(m.code)}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <div className="font-medium">{m.libelle}</div>
                    <div className="text-xs text-muted-foreground">
                      {m.est_transparent && (
                        <span className="mr-2 rounded bg-amber-100 px-1.5 py-0.5 text-amber-900">
                          transparent
                        </span>
                      )}
                      {m.grammage_gm2 && `${m.grammage_gm2} g/m²`}
                      {m.epaisseur_microns && `${m.epaisseur_microns} µm`}
                      {m.opacite_pct != null && (
                        <span className="ml-2">
                          opacité {m.opacite_pct} %
                        </span>
                      )}
                    </div>
                  </div>
                  {m.notes_techniques && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {m.notes_techniques}
                    </p>
                  )}
                </CheckboxRow>
              ))}
            </div>
          </section>
        ))}
      </CardContent>
    </Card>
  );
}

function StepOptions({
  groups,
  selection,
  onToggle,
}: {
  groups: Record<string, OnboardingOptionDefault[]>;
  selection: Set<string>;
  onToggle: (code: string) => void;
}) {
  // Ordre métier des catégories — Impression → Finition → ... → Sécurité
  const categoryOrder = [
    "Impression",
    "Finition",
    "Découpe",
    "Relief",
    "Données variables",
    "Réglementaire",
    "Sécurité",
    "Encre spéciale",
    "Intelligent",
    "Construction",
    "Conditionnement",
  ];
  const orderedCats = categoryOrder.filter((c) => groups[c]);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Étape 4 — Vos options de fabrication</CardTitle>
        <CardDescription>
          20 options standard du marché. Décochez celles que vous ne savez
          pas faire — coefficients vitesse/gâche et temps de calage sont
          ajustables ensuite.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {orderedCats.map((cat) => (
          <section key={cat}>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {cat}
            </h3>
            <div className="space-y-2">
              {groups[cat].map((o) => (
                <CheckboxRow
                  key={o.code}
                  id={`opt-${o.code}`}
                  checked={selection.has(o.code)}
                  onChange={() => onToggle(o.code)}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <div className="font-medium">{o.libelle}</div>
                    <div className="text-xs text-muted-foreground">
                      vitesse ×{o.coef_vitesse_impact} • gâche ×
                      {o.coef_gache_impact} • calage +
                      {o.ajoute_temps_calage_min} min
                    </div>
                  </div>
                  {o.description && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {o.description}
                    </p>
                  )}
                </CheckboxRow>
              ))}
            </div>
          </section>
        ))}
      </CardContent>
    </Card>
  );
}

function StepRecap({
  defaults,
  selection,
}: {
  defaults: OnboardingCatalogueDefaults;
  selection: Selection;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Récapitulatif — prêt à initialiser</CardTitle>
        <CardDescription>
          Vérifiez avant validation. Les 4 barèmes flexo (échenillage, effet
          banane, confort de roulage, compensation laize/dev) seront créés
          automatiquement — ils sont indispensables au moteur d&apos;optimisation
          et restent ajustables à tout moment.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <RecapLine
          label="Machines"
          count={selection.machines.size}
          total={defaults.machines.length}
        />
        <RecapLine
          label="Cylindres magnétiques"
          count={selection.cylindres.size}
          total={defaults.cylindres_developpes_mm.length}
        />
        <RecapLine
          label="Matières"
          count={selection.matieres.size}
          total={defaults.matieres.length}
        />
        <RecapLine
          label="Options de fabrication"
          count={selection.options.size}
          total={defaults.options.length}
        />
        <RecapLine
          label="Barèmes flexo (automatiques)"
          count={defaults.baremes.length}
          total={defaults.baremes.length}
        />
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <strong>Important :</strong> cette opération n&apos;est faisable
          qu&apos;une fois. Une fois validée, le catalogue est créé dans
          votre tenant et vous arrivez sur l&apos;écran de saisie devis.
          Vous pourrez ensuite ajouter/modifier chaque élément depuis vos
          paramètres.
        </div>
      </CardContent>
    </Card>
  );
}

function RecapLine({
  label,
  count,
  total,
}: {
  label: string;
  count: number;
  total: number;
}) {
  return (
    <div className="flex items-baseline justify-between border-b border-border pb-2 last:border-0">
      <span className="text-sm">{label}</span>
      <span className="text-sm font-medium">
        {count} / {total} sélectionné{count > 1 ? "s" : ""}
      </span>
    </div>
  );
}
