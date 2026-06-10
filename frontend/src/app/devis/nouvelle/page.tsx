"use client";

/**
 * Lot front — devis en UNE page scrollable réactive (remplace à terme le
 * wizard 4 étapes). Route AUTONOME `/devis/nouvelle` : le wizard
 * (`/optimisation`, `/devis/nouveau`) reste intact tant que cette page n'est
 * pas validée en preview. Pas de big-bang.
 *
 * Réactivité : à chaque saisie (debounce 250 ms + AbortController) →
 * `previewDevisLive` (POST /api/devis/preview, #124, read-only cost_engine) →
 * maj hero prix + €/1000 + marge + décompo + géométrie + alertes. On garde le
 * dernier résultat pendant le recalcul. « Valider » → `createDevis`.
 *
 * Design FlexoSuite : accent/CTA orange (#E85D2F), gains/refente vert,
 * info/aide bleu, fond papier chaud. La couleur PORTE du sens.
 *
 * HORS scope (lot front B) : optim de pose auto (3 cartes config). Ici l'Outil
 * est un select des cylindres compatibles → `cylindre_id` (null en sans outil).
 */
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  createDevis,
  getEntreprise,
  getOptionsDisponibles,
  listClients,
  listCylindres,
  listMachines,
  listMatieres,
  updateMatiereEpaisseur,
  type Client,
  type CylindreParc,
  type Machine,
  type MatiereOut,
  type OptionDisponible,
} from "@/lib/api";

import {
  cylindresCompatibles,
  posesPourPersist,
  previewDevisLive,
  type DevisPreviewInput,
  type DevisPreviewResult,
} from "./devisPreview";

// Palette FlexoSuite : accent/CTA orange #E85D2F (classes Tailwind arbitraires
// text-[#E85D2F] / bg-[#E85D2F]), gains/refente emerald, info/aide bleu, fond
// papier chaud #FBF7F0. La couleur porte du sens.

function eur(n: number | null): string {
  if (n === null) return "—";
  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// mm avec décimales FR (ex. 2.55 → « 2,55 »).
function mm(n: number): string {
  return n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

// Libellés des sens d'enroulement (codes SE ; 0/9 = sans impression).
const SENS_LABEL: Record<number, string> = {
  0: "0° ext. sans impr.",
  1: "0° ext. droite",
  2: "180° ext. gauche",
  3: "270° ext. pied",
  4: "90° ext. tête",
  5: "0° int. droite",
  6: "180° int. gauche",
  7: "270° int. pied",
  8: "90° int. tête",
  9: "0° int. sans impr.",
};
const sensLabel = (n: number): string => SENS_LABEL[n] ?? `Sens ${n}`;

export default function DevisPageUnique() {
  const router = useRouter();
  const { toast } = useToast();

  // ── Données parc (chargées au mount) ──────────────────────────────
  const [matieres, setMatieres] = useState<MatiereOut[]>([]);
  const [cylindres, setCylindres] = useState<CylindreParc[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [optionsDispo, setOptionsDispo] = useState<OptionDisponible[]>([]);
  const [clients, setClients] = useState<Client[]>([]);

  // ── Saisie (état local de la page) ────────────────────────────────
  // Client (optionnel) : sa sélection pré-remplit le profil bobine.
  const [clientId, setClientId] = useState<number | null>(null);
  const [laize, setLaize] = useState("100");
  const [dev, setDev] = useState("80");
  const [quantite, setQuantite] = useState("10000");
  const [nbCouleurs, setNbCouleurs] = useState("4");
  // Mode « format sans outil » (impression pleine largeur + refente).
  const [modeSansOutil, setModeSansOutil] = useState(false);
  const [laizeStock, setLaizeStock] = useState("");
  const [nbFillesForce, setNbFillesForce] = useState("");
  // Outil : cylindre + machine (alimentent le lot persisté).
  const [machineId, setMachineId] = useState<number | null>(null);
  const [cylindreId, setCylindreId] = useState<number | null>(null);
  // Lot C — config outil×machine choisie (cartes/table) + table dépliée.
  // id = identifiant composite du back (string, ex. "1-1-4x2").
  const [configId, setConfigId] = useState<string | null>(null);
  const [showAllConfigs, setShowAllConfigs] = useState(false);
  // Lot C — écarts entre étiquettes (forçables Règle 7).
  const [intervalleLaize, setIntervalleLaize] = useState("");
  const [forceIntervalleLaize, setForceIntervalleLaize] = useState(false);
  const [nbPosesLaizeForce, setNbPosesLaizeForce] = useState(""); // "" = auto
  // Matière.
  const [matiereId, setMatiereId] = useState<number | null>(null);
  const [epaisseur, setEpaisseur] = useState("150");
  // Lot E — enregistrement d'une épaisseur manquante au catalogue (PATCH).
  const [savingEpaisseur, setSavingEpaisseur] = useState(false);
  // Bobinage.
  const [mandrin, setMandrin] = useState("76");
  const [diametreMax, setDiametreMax] = useState("");
  const [sens, setSens] = useState("1");
  // Finitions.
  const [optionsCodes, setOptionsCodes] = useState<Set<string>>(new Set());
  // Bord latéral (défaut entreprise, rempli au mount).
  const [bordLateral, setBordLateral] = useState("10");
  // V0 — Commercial : marge % (override, "" = défaut tenant) + remise %.
  const [margePct, setMargePct] = useState("");
  const [remisePct, setRemisePct] = useState("0");

  // Preview : `preview` = dernier résultat valide (gardé pendant un recalcul),
  // `recomputing` = un recalcul est en vol. `null` = sous le minimum requis.
  const [preview, setPreview] = useState<DevisPreviewResult | null>(null);
  const [recomputing, setRecomputing] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [mats, cyls, machs, opts, ent, clis] = await Promise.all([
          listMatieres(),
          listCylindres(true),
          listMachines(),
          getOptionsDisponibles(),
          getEntreprise(),
          listClients(),
        ]);
        if (cancelled) return;
        setMatieres(mats);
        setCylindres(cyls);
        const actives = machs.filter((m) => m.actif);
        setMachines(actives);
        if (actives.length >= 1) setMachineId(actives[0]!.id);
        setOptionsDispo(opts);
        setClients(clis);
        const chute = parseFloat(ent.chute_laterale_min_mm);
        if (Number.isFinite(chute)) setBordLateral(String(chute));
      } catch (err) {
        if (!cancelled)
          toast({
            title: "Chargement impossible",
            description: err instanceof Error ? err.message : "Erreur inconnue",
            variant: "destructive",
          });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [toast]);

  // Matière sélectionnée → auto-fill épaisseur (catalogue prime).
  const matiereSel = useMemo(
    () => matieres.find((m) => m.id === matiereId) ?? null,
    [matieres, matiereId],
  );
  useEffect(() => {
    if (matiereSel?.epaisseur_microns) {
      setEpaisseur(String(matiereSel.epaisseur_microns));
    }
  }, [matiereSel]);

  // Client sélectionné → pré-remplit le profil bobine (Sprint 16, mêmes
  // champs que l'étape rebobinage du wizard). On n'écrase qu'au CHANGEMENT de
  // client (ref `lastClient`) pour ne pas reclober les saisies manuelles ; les
  // champs null du client laissent le défaut tracé (mandrin 76). Les
  // intervalles ne font pas partie du profil client (constantes cost_engine).
  const lastClientApplied = useRef<number | null>(null);
  useEffect(() => {
    if (clientId === lastClientApplied.current) return;
    lastClientApplied.current = clientId;
    const cli = clients.find((c) => c.id === clientId) ?? null;
    if (cli === null) return;
    if (cli.diametre_mandrin_mm !== null) {
      setMandrin(String(cli.diametre_mandrin_mm));
    }
    if (cli.diametre_max_bobine_mm !== null) {
      setDiametreMax(String(cli.diametre_max_bobine_mm));
    }
    if (cli.sens_enroulement !== null) {
      setSens(String(cli.sens_enroulement));
    }
  }, [clientId, clients]);

  // Cylindres compatibles avec le format (filtre géométrique front).
  const cylindresOk = useMemo(
    () => cylindresCompatibles(cylindres, parseFloat(dev) || 0, 2),
    [cylindres, dev],
  );
  // Si le cylindre choisi n'est plus compatible (format changé) → reset.
  useEffect(() => {
    if (cylindreId !== null && !cylindresOk.some((c) => c.id === cylindreId)) {
      setCylindreId(null);
    }
  }, [cylindresOk, cylindreId]);

  // ── Preview live (POST /api/devis/preview) ────────────────────────
  // Développé du cylindre choisi — sert uniquement aux poses de persistance
  // (le endpoint résout cylindre_id côté serveur pour la preview).
  const cylindreDeveloppe = useMemo(() => {
    if (cylindreId === null) return null;
    const c = cylindres.find((x) => x.id === cylindreId);
    return c ? parseFloat(c.developpe_mm) : null;
  }, [cylindres, cylindreId]);

  const previewInput = useMemo<DevisPreviewInput>(
    () => ({
      laize_mm: parseFloat(laize) || 0,
      dev_mm: parseFloat(dev) || 0,
      forme: null,
      quantite: parseInt(quantite, 10) || 0,
      nb_couleurs: parseInt(nbCouleurs, 10) || 0,
      cylindre_id: modeSansOutil ? null : cylindreId,
      // Presse requise pour le chiffrage même en sans outil (refente incluse).
      machine_id: machineId,
      matiere_id: matiereId,
      epaisseur_um: parseFloat(epaisseur) || null,
      mandrin_mm: parseInt(mandrin, 10) || 76,
      diam_max_mm: diametreMax.trim() !== "" ? parseFloat(diametreMax) : null,
      nb_filles_force:
        modeSansOutil && nbFillesForce.trim() !== ""
          ? parseInt(nbFillesForce, 10)
          : null,
      mode_sans_outil: modeSansOutil,
      laize_stock_mm:
        modeSansOutil && laizeStock.trim() !== ""
          ? parseFloat(laizeStock)
          : null,
      options_codes: Array.from(optionsCodes),
      // Lot C-inputs (#140) — la config + le forçage écarts bougent la marge.
      config_id: modeSansOutil ? null : configId,
      force_intervalle_laize: forceIntervalleLaize,
      intervalle_laize_mm:
        intervalleLaize.trim() !== "" ? parseFloat(intervalleLaize) : null,
      nb_poses_laize_force:
        nbPosesLaizeForce.trim() !== ""
          ? parseInt(nbPosesLaizeForce, 10)
          : null,
      marge_pct_override: margePct.trim() !== "" ? parseFloat(margePct) : null,
      remise_pct: remisePct.trim() !== "" ? parseFloat(remisePct) : 0,
    }),
    [
      laize,
      dev,
      quantite,
      nbCouleurs,
      modeSansOutil,
      laizeStock,
      nbFillesForce,
      cylindreId,
      machineId,
      matiereId,
      epaisseur,
      mandrin,
      diametreMax,
      optionsCodes,
      configId,
      forceIntervalleLaize,
      intervalleLaize,
      nbPosesLaizeForce,
      margePct,
      remisePct,
    ],
  );

  // Champs minimaux pour estimer : sous ce seuil on NE déclenche PAS l'appel
  // preview (perf) et le hero affiche une invite plutôt qu'un faux 0 €.
  const miniPresents =
    previewInput.laize_mm > 0 &&
    previewInput.dev_mm > 0 &&
    previewInput.quantite > 0;

  // Recalc réactif : 1er rendu = appel immédiat (pas de flash d'attente), puis
  // debounce 250 ms + AbortController (annule la requête en vol). On GARDE le
  // dernier résultat affiché pendant le recalcul (pas de clignotement).
  const firstRun = useRef(true);
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    abortRef.current?.abort();
    if (!miniPresents) {
      setPreview(null);
      setRecomputing(false);
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setRecomputing(true);
    const run = () => {
      previewDevisLive(previewInput, { signal: controller.signal })
        .then((res) => {
          if (!controller.signal.aborted) {
            setPreview(res);
            setRecomputing(false);
          }
        })
        .catch((err) => {
          // AbortError = recalcul remplacé → ignore. Autre erreur → on garde
          // le dernier résultat et on arrête le spinner.
          if (
            (err as DOMException)?.name !== "AbortError" &&
            !controller.signal.aborted
          ) {
            setRecomputing(false);
          }
        });
    };
    if (firstRun.current) {
      firstRun.current = false;
      run();
      return () => controller.abort();
    }
    const handle = setTimeout(run, 250);
    return () => {
      clearTimeout(handle);
      controller.abort();
    };
  }, [previewInput, miniPresents]);

  // ── Lot C : configs outil×machine & écarts (depuis la preview) ────
  const configsTries = useMemo(
    () => [...(preview?.configs ?? [])].sort((a, b) => b.score - a.score),
    [preview],
  );
  const configsRecommandees = useMemo(
    () => configsTries.filter((c) => c.recommande).slice(0, 3),
    [configsTries],
  );
  const selectedConfig = useMemo(
    () => configsTries.find((c) => c.id === configId) ?? null,
    [configsTries, configId],
  );
  const ecarts = preview?.ecarts ?? null;

  // Auto-sélection de la meilleure config quand la liste arrive (ou que la
  // sélection courante n'existe plus). Pas en mode sans outil (pas d'outil).
  useEffect(() => {
    if (modeSansOutil || configsTries.length === 0) return;
    if (configId !== null && configsTries.some((c) => c.id === configId)) return;
    setConfigId(configsTries[0]!.id);
  }, [configsTries, configId, modeSansOutil]);

  // Config choisie → résout cylindre_id + machine_id depuis le parc (le lot
  // persisté garde sa shape ; le serveur épingle aussi via config_id).
  useEffect(() => {
    if (selectedConfig === null) return;
    const cyl = cylindres.find(
      (c) => c.nb_dents === selectedConfig.cylindre_dents,
    );
    if (cyl) setCylindreId(cyl.id);
    const mach = machines.find((m) => m.nom === selectedConfig.machine);
    if (mach) setMachineId(mach.id);
  }, [selectedConfig, cylindres, machines]);

  // Écarts : pré-remplit l'intervalle laize depuis le défaut moteur tant que
  // l'utilisateur ne force pas (Règle 7).
  useEffect(() => {
    if (ecarts && !forceIntervalleLaize) {
      setIntervalleLaize(String(ecarts.intervalle_laize_mm));
    }
  }, [ecarts, forceIntervalleLaize]);

  const toggleOption = (code: string) =>
    setOptionsCodes((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });

  const peutValider =
    parseFloat(laize) > 0 &&
    parseFloat(dev) > 0 &&
    parseInt(quantite, 10) > 0 &&
    matiereId !== null &&
    machineId !== null &&
    (modeSansOutil || cylindreId !== null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!peutValider || machineId === null) return;
    // Poses pour la persistance : la config choisie (Lot C) fait foi ; sinon
    // best-effort local (le backend recalcule via le cost_engine à la création).
    const posesFallback = posesPourPersist(previewInput, cylindreDeveloppe);
    const nbPosesDev =
      !modeSansOutil && selectedConfig
        ? selectedConfig.poses_dev
        : posesFallback.nb_poses_dev;
    const nbFilles =
      !modeSansOutil && selectedConfig
        ? selectedConfig.poses_laize
        : posesFallback.nb_poses_laize;
    setSubmitting(true);
    try {
      const devis = await createDevis({
        client_id: clientId,
        payload_input: {
          format_etiquette_largeur_mm: parseFloat(laize),
          format_etiquette_hauteur_mm: parseFloat(dev),
          mandrin_mm: parseInt(mandrin, 10),
          mode_calcul: "manuel",
          source: "devis_page_unique",
          mode_sans_outil: modeSansOutil,
          laize_stock_mm:
            modeSansOutil && laizeStock.trim() !== ""
              ? parseFloat(laizeStock)
              : null,
          nb_couleurs: {
            impression: parseInt(nbCouleurs, 10) || 0,
            pantone: 0,
            blanc: 0,
            vernis: 0,
          },
          options_codes_etape4: Array.from(optionsCodes),
        },
        payload_output: {},
        quantite_totale: parseInt(quantite, 10),
        lots: [
          {
            cylindre_id: modeSansOutil ? null : cylindreId,
            machine_id: machineId,
            nb_poses_dev: nbPosesDev,
            nb_poses_laize: nbFilles,
            sens_enroulement: parseInt(sens, 10) || 1,
            quantite: parseInt(quantite, 10),
            matiere_id: matiereId as number,
            bord_lateral_mm: bordLateral,
          },
        ],
      });
      toast({
        title: "Devis créé ✓",
        description: `Devis ${devis.numero} créé.`,
      });
      router.push(`/devis/${devis.id}`);
    } catch (err) {
      toast({
        title: "Création impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Lot E — enregistre l'épaisseur saisie dans le catalogue matière (PATCH),
  // puis recharge les matières → le fallback se lève et /preview recalcule.
  const handleSaveEpaisseur = async () => {
    const um = parseFloat(epaisseur);
    if (matiereId === null || !(um > 0)) return;
    setSavingEpaisseur(true);
    try {
      await updateMatiereEpaisseur(matiereId, { epaisseur_um: um });
      const mats = await listMatieres();
      setMatieres(mats);
      toast({
        title: "Épaisseur enregistrée ✓",
        description: `${um} µm ajoutés au catalogue matière.`,
      });
    } catch (err) {
      toast({
        title: "Enregistrement impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSavingEpaisseur(false);
    }
  };

  const geo = preview?.geometrie;

  // Delta marginal par code (depuis preview.options) pour les chips finitions
  // + couleur_plus. Le serveur price ; le front ne fait qu'afficher.
  const optionByCode = useMemo(() => {
    const m = new Map<string, DevisPreviewResult["options"][number]>();
    for (const o of preview?.options ?? []) m.set(o.code, o);
    return m;
  }, [preview]);
  const couleurPlus = optionByCode.get("couleur_plus") ?? null;

  // Libellé « + X € » d'un levier (option/couleur) : impact production sans
  // forfait → « chiffré bientôt », jamais « +0 € ».
  const coutLevier = (o: DevisPreviewResult["options"][number] | null): string => {
    if (o === null) return "";
    if (o.delta_eur === null || o.impact_production) {
      return "impact production (chiffré bientôt)";
    }
    return `+${eur(o.delta_eur)} €`;
  };

  return (
    <main className="min-h-screen bg-[#FBF7F0]">
      <form
        onSubmit={handleSubmit}
        className="mx-auto max-w-6xl p-4 pb-24 sm:p-6 lg:pb-6"
      >
        <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
          {/* ── Panneau prix : rail sticky droite (desktop). Sur mobile, la
              barre basse fixe ci-dessous prend le relais (ce panneau est
              masqué). ──────────────────────────────────────────────────── */}
          <aside className="hidden self-start lg:col-start-2 lg:row-start-1 lg:flex lg:flex-col lg:gap-3 lg:sticky lg:top-4">
            <div
              data-testid="hero-prix"
              className="rounded-xl border border-[#E85D2F]/30 bg-white/95 p-5 shadow-md backdrop-blur"
            >
          <div className="flex items-baseline justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Prix HT facturé (net remise)
            </p>
            {recomputing && (
              <span
                data-testid="hero-recompute"
                className="text-xs text-muted-foreground"
                aria-live="polite"
              >
                recalcul…
              </span>
            )}
          </div>
          {recomputing && !preview && miniPresents ? (
            <div
              data-testid="hero-skeleton"
              className="mt-2 space-y-2"
              aria-hidden="true"
            >
              <div className="h-8 w-32 animate-pulse rounded bg-muted" />
              <div className="h-3 w-48 animate-pulse rounded bg-muted" />
            </div>
          ) : !miniPresents || !preview || preview.prix_ht === null ? (
            <p
              data-testid="hero-incomplet"
              className="mt-1 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800"
            >
              ⓘ{" "}
              {!miniPresents
                ? "Renseigne laize, développé et quantité pour estimer le prix."
                : "Complète la sélection (matière, cylindre…) — voir les indications ci-dessous."}
            </p>
          ) : (
            <div className="mt-1 space-y-2">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span
                  data-testid="hero-prix-valeur"
                  className="text-3xl font-bold text-[#E85D2F]"
                >
                  {eur(preview.prix_ht_net ?? preview.prix_ht)} €
                </span>
                <span
                  data-testid="hero-prix-1000"
                  className="text-sm font-medium text-foreground"
                >
                  {eur(preview.prix_1000)} € / 1000
                </span>
                {preview.marge_pct !== null && (
                  <span
                    data-testid="hero-marge"
                    className="rounded bg-emerald-100 px-2 py-0.5 text-sm font-semibold text-emerald-800"
                  >
                    marge {Math.round(preview.marge_pct)} %
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                revient {eur(preview.cout_revient)} €
              </p>
              {/* V0 — le gros prix EST le HT net ; ici on trace le brut + la
                  remise commerciale appliquée par-dessus (ligne séparée). */}
              {preview.remise_eur !== null && preview.remise_eur > 0 && (
                <div
                  data-testid="hero-remise"
                  className="rounded-md bg-emerald-50 px-2.5 py-1.5 text-xs text-emerald-800"
                >
                  HT brut {eur(preview.prix_ht)} € · remise{" "}
                  {Math.round(preview.remise_pct)} % (−{eur(preview.remise_eur)}{" "}
                  €)
                </div>
              )}
              {/* V0 — décompo coût groupée (5 lignes métier). */}
              {preview.decompo_groupee && (
                <dl
                  data-testid="hero-decompo-groupee"
                  className="space-y-0.5 border-t border-border pt-2 text-xs"
                >
                  {(
                    [
                      ["Matière (P1)", preview.decompo_groupee.matiere_p1],
                      [
                        "Impression + presse + calage",
                        preview.decompo_groupee.impression_presse_calage,
                      ],
                      ["Clichés / outil", preview.decompo_groupee.cliches_outil],
                      ["Finitions", preview.decompo_groupee.option_finitions],
                      ["Refente", preview.decompo_groupee.refente],
                    ] as const
                  )
                    .filter(([, v]) => v > 0)
                    .map(([label, v]) => (
                      <div key={label} className="flex justify-between gap-2">
                        <dt className="text-muted-foreground">{label}</dt>
                        <dd className="font-mono">{eur(v)} €</dd>
                      </div>
                    ))}
                  <div className="flex justify-between gap-2 border-t border-border pt-1 font-semibold text-foreground">
                    <dt>Total HT{preview.remise_eur ? " net" : ""}</dt>
                    <dd className="font-mono text-[#B8431D]">
                      {eur(preview.prix_ht_net ?? preview.prix_ht)} €
                    </dd>
                  </div>
                </dl>
              )}
            </div>
          )}
          {preview && preview.alertes.length > 0 && (
            <ul data-testid="hero-alertes" className="mt-3 space-y-1">
              {preview.alertes.map((a, i) => (
                <li
                  key={i}
                  className={
                    "rounded-md px-2.5 py-1.5 text-xs " +
                    (a.niveau === "warn"
                      ? "bg-amber-50 text-amber-800"
                      : "bg-blue-50 text-blue-800")
                  }
                >
                  {a.niveau === "warn" ? "⚠ " : "ⓘ "}
                  {a.message}
                </li>
              ))}
            </ul>
          )}
            </div>
            {/* Valider — dans le rail prix. */}
            <Button
              type="submit"
              size="lg"
              disabled={!peutValider || submitting}
              data-testid="valider"
              className="w-full bg-[#E85D2F] px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:bg-[#d24f24] disabled:opacity-50"
            >
              {submitting ? "Création…" : "Valider le devis"}
            </Button>
            <p className="px-1 text-center text-xs text-muted-foreground">
              {peutValider
                ? "Prêt à créer le devis."
                : "Renseigne format, quantité, matière" +
                  (modeSansOutil ? "." : ", machine et cylindre.")}
            </p>
          </aside>

          {/* ── Colonne formulaire ─────────────────────────────────── */}
          <div className="space-y-5 lg:col-start-1 lg:row-start-1 lg:min-w-0">
            {/* ── Client (optionnel) — pré-remplit le profil bobine ──── */}
            <SectionCard title="Client">
          <Field label="Client (pré-remplit Ø mandrin, Ø max, sens)">
            <select
              className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={clientId ?? ""}
              onChange={(e) => setClientId(Number(e.target.value) || null)}
              data-testid="d-client"
              aria-label="Client"
            >
              <option value="">— Aucun (saisie manuelle) —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.raison_sociale}
                </option>
              ))}
            </select>
          </Field>
        </SectionCard>

        {/* ── Format ───────────────────────────────────────────────── */}
        <SectionCard title="Format & impression" accent>
          <div className="rounded-md border border-border bg-muted/30 p-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[#E85D2F]"
                checked={modeSansOutil}
                onChange={(e) => setModeSansOutil(e.target.checked)}
                data-testid="toggle-sans-outil"
              />
              Format sans outil (impression pleine largeur + refente)
            </label>
            {/* Champs sans-outil : apparition/disparition en transition douce. */}
            <Collapsible open={modeSansOutil} testId="sans-outil-fields">
              <div className="mt-3 grid grid-cols-2 gap-3">
                <Field label="Laize bobine stock (mm) *">
                  <Input
                    type="number"
                    min={1}
                    step="0.1"
                    value={laizeStock}
                    onChange={(e) => setLaizeStock(e.target.value)}
                    data-testid="laize-stock"
                    tabIndex={modeSansOutil ? undefined : -1}
                  />
                </Field>
                <Field label="Nb bobines filles (optionnel)">
                  <Input
                    type="number"
                    min={1}
                    value={nbFillesForce}
                    onChange={(e) => setNbFillesForce(e.target.value)}
                    placeholder="auto"
                    data-testid="nb-filles"
                    tabIndex={modeSansOutil ? undefined : -1}
                  />
                </Field>
              </div>
            </Collapsible>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Laize (mm)">
              <Input
                type="number"
                min={1}
                step="0.1"
                value={laize}
                onChange={(e) => setLaize(e.target.value)}
                data-testid="f-laize"
                required
              />
            </Field>
            <Field label="Développé (mm)">
              <Input
                type="number"
                min={1}
                step="0.1"
                value={dev}
                onChange={(e) => setDev(e.target.value)}
                data-testid="f-dev"
                required
              />
            </Field>
            <Field label="Quantité (étiquettes)">
              <Input
                type="number"
                min={1}
                value={quantite}
                onChange={(e) => setQuantite(e.target.value)}
                data-testid="f-qte"
                required
              />
            </Field>
            <Field label="Nb couleurs impression">
              <Input
                type="number"
                min={0}
                value={nbCouleurs}
                onChange={(e) => setNbCouleurs(e.target.value)}
                data-testid="f-couleurs"
              />
            </Field>
          </div>
        </SectionCard>

        {/* ── Outil ──────────────────────────────────────────────────
            Replié (transition douce) en mode sans outil plutôt que démonté :
            les contrôles passent hors tab-order (tabIndex -1) + aria-hidden. */}
        <Collapsible open={!modeSansOutil} testId="outil-section">
          <SectionCard title="Choix outil & pose">
            {configsTries.length > 0 ? (
              <>
                <p className="text-sm text-muted-foreground">
                  Le moteur propose les meilleures configs (cylindre × machine).
                  Choisis-en une — chaque config = un développé Z = une pose.
                </p>
                {/* 3 cartes recommandées (score décroissant). */}
                <div className="grid gap-3 sm:grid-cols-3">
                  {configsRecommandees.map((c) => {
                    const actif = c.id === configId;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        aria-pressed={actif ? "true" : "false"}
                        onClick={() => setConfigId(c.id)}
                        data-testid={`config-card-${c.id}`}
                        tabIndex={modeSansOutil ? -1 : undefined}
                        className={
                          "rounded-xl border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D2F]/60 " +
                          (actif
                            ? "border-2 border-[#E85D2F] bg-[#E85D2F]/5"
                            : "border-border bg-white hover:border-[#E85D2F]/50")
                        }
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-semibold">
                            {c.cylindre_dents} dents · {mm(c.developpe_mm)} mm
                          </span>
                          <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-bold text-emerald-800">
                            {c.score}
                          </span>
                        </div>
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {c.machine}
                        </div>
                        <div className="mt-1.5 text-xs">
                          <strong>
                            {c.poses_laize}×{c.poses_dev} = {c.poses_total} poses
                          </strong>{" "}
                          · Δdev {mm(c.delta_dev_mm)} · Δlaize{" "}
                          {mm(c.delta_laize_mm)}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Voir toutes les configs (table repliable). */}
                <button
                  type="button"
                  onClick={() => setShowAllConfigs((v) => !v)}
                  data-testid="toggle-configs"
                  aria-expanded={showAllConfigs ? "true" : "false"}
                  className="text-sm font-semibold text-[#B8431D]"
                >
                  {showAllConfigs ? "▴" : "▾"} Voir les {configsTries.length}{" "}
                  configurations
                </button>
                <Collapsible open={showAllConfigs} testId="configs-table">
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse text-xs">
                      <thead>
                        <tr className="text-left text-muted-foreground">
                          <th className="border-b border-border p-2">
                            Cylindre (développé)
                          </th>
                          <th className="border-b border-border p-2">Machine</th>
                          <th className="border-b border-border p-2">Poses</th>
                          <th className="border-b border-border p-2">Δ dev</th>
                          <th className="border-b border-border p-2">Δ laize</th>
                          <th className="border-b border-border p-2">Score</th>
                          <th className="border-b border-border p-2">Sens</th>
                        </tr>
                      </thead>
                      <tbody>
                        {configsTries.map((c) => {
                          const actif = c.id === configId;
                          return (
                            <tr
                              key={c.id}
                              onClick={() => setConfigId(c.id)}
                              data-testid={`config-row-${c.id}`}
                              className={
                                "cursor-pointer " +
                                (actif ? "bg-[#E85D2F]/10" : "hover:bg-muted/40")
                              }
                            >
                              <td className="border-b border-border p-2">
                                {mm(c.developpe_mm)} mm · {c.cylindre_dents} d
                              </td>
                              <td className="border-b border-border p-2">
                                {c.machine}
                              </td>
                              <td className="border-b border-border p-2">
                                {c.poses_laize}×{c.poses_dev}={c.poses_total}
                              </td>
                              <td className="border-b border-border p-2">
                                {mm(c.delta_dev_mm)}
                              </td>
                              <td className="border-b border-border p-2">
                                {mm(c.delta_laize_mm)}
                              </td>
                              <td className="border-b border-border p-2">
                                {c.score}
                              </td>
                              <td className="border-b border-border p-2">
                                {sensLabel(c.sens)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </Collapsible>
              </>
            ) : (
              /* Fallback tant que /preview ne renvoie pas encore les configs
                 (ancien endpoint / état trop partiel) : sélection manuelle. */
              <div className="grid grid-cols-2 gap-3">
                {machines.length > 1 ? (
                  <Field label="Machine">
                    <select
                      className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={machineId ?? ""}
                      onChange={(e) =>
                        setMachineId(Number(e.target.value) || null)
                      }
                      data-testid="o-machine"
                      aria-label="Machine"
                      tabIndex={modeSansOutil ? -1 : undefined}
                    >
                      {machines.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.nom}
                        </option>
                      ))}
                    </select>
                  </Field>
                ) : (
                  <Field label="Machine">
                    <p
                      data-testid="o-machine-unique"
                      className="rounded-md border border-input bg-muted/40 px-3 py-2 text-sm"
                    >
                      {machines[0]?.nom ?? "—"}
                    </p>
                  </Field>
                )}
                <Field label="Cylindre compatible">
                  <select
                    className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={cylindreId ?? ""}
                    onChange={(e) =>
                      setCylindreId(Number(e.target.value) || null)
                    }
                    data-testid="o-cylindre"
                    aria-label="Cylindre compatible"
                    tabIndex={modeSansOutil ? -1 : undefined}
                  >
                    <option value="">— Choisir un cylindre —</option>
                    {cylindresOk.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nb_dents} dents · ø {c.developpe_mm} mm
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
            )}

            {/* Écarts entre étiquettes (forçables Règle 7). */}
            <div className="rounded-md border border-border bg-muted/30 p-3">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Écarts entre étiquettes
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Intervalle laize (mm)">
                  <Input
                    type="number"
                    min={0.1}
                    max={50}
                    step="0.1"
                    value={intervalleLaize}
                    onChange={(e) => setIntervalleLaize(e.target.value)}
                    disabled={!forceIntervalleLaize}
                    data-testid="ec-intervalle-laize"
                    tabIndex={modeSansOutil ? -1 : undefined}
                  />
                  <label className="mt-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <input
                      type="checkbox"
                      className="h-3.5 w-3.5 accent-[#E85D2F]"
                      checked={forceIntervalleLaize}
                      onChange={(e) =>
                        setForceIntervalleLaize(e.target.checked)
                      }
                      data-testid="ec-force-laize"
                    />
                    forcer (Règle 7)
                  </label>
                </Field>
                <Field label="Nb poses laize">
                  <select
                    className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={nbPosesLaizeForce === "" ? "auto" : "force"}
                    onChange={(e) =>
                      setNbPosesLaizeForce(
                        e.target.value === "auto"
                          ? ""
                          : String(selectedConfig?.poses_laize ?? 1),
                      )
                    }
                    data-testid="ec-nb-poses-mode"
                    aria-label="Nb poses laize"
                    tabIndex={modeSansOutil ? -1 : undefined}
                  >
                    <option value="auto">Auto (moteur)</option>
                    <option value="force">Forcer N poses</option>
                  </select>
                  {nbPosesLaizeForce !== "" && (
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={nbPosesLaizeForce}
                      onChange={(e) => setNbPosesLaizeForce(e.target.value)}
                      data-testid="ec-nb-poses-n"
                      className="mt-1.5"
                    />
                  )}
                </Field>
              </div>
              <p className="mt-2 text-xs text-blue-700">
                🛡 Souveraineté Règle 7 — tu peux forcer/écraser n&apos;importe
                quel choix du moteur ; chaque forçage est tracé sur le devis.
              </p>
            </div>
          </SectionCard>
        </Collapsible>

        {/* ── Matière (Lot E) ──────────────────────────────────────── */}
        <SectionCard title="Matière">
          {/* Bandeau fallback épaisseur — VISIBLE (pas de tooltip survol). */}
          {geo?.epaisseur_fallback && (
            <div
              data-testid="m-fallback"
              className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800"
            >
              ⚠ Épaisseur inconnue — Ø estimé à 150 µm. Renseigne
              l&apos;épaisseur ↓
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Matière *">
              <select
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={matiereId ?? ""}
                onChange={(e) => setMatiereId(Number(e.target.value) || null)}
                data-testid="m-matiere"
                aria-label="Matière"
              >
                <option value="">— Choisir —</option>
                {matieres.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.libelle}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Épaisseur (µm)">
              <Input
                type="number"
                min={1}
                value={epaisseur}
                onChange={(e) => setEpaisseur(e.target.value)}
                data-testid="m-epaisseur"
              />
              {/* Persiste l'épaisseur saisie au catalogue (PATCH matière). */}
              {matiereId !== null && parseFloat(epaisseur) > 0 && (
                <button
                  type="button"
                  onClick={handleSaveEpaisseur}
                  disabled={savingEpaisseur}
                  data-testid="m-save-epaisseur"
                  className="mt-1 text-xs font-semibold text-[#B8431D] disabled:opacity-50"
                >
                  {savingEpaisseur
                    ? "Enregistrement…"
                    : "Enregistrer cette épaisseur au catalogue ↑"}
                </button>
              )}
            </Field>
          </div>
          {/* Ø bobine en direct (depuis la géométrie /preview). */}
          {geo?.diametre_mm != null && (
            <p data-testid="m-diametre" className="text-sm text-muted-foreground">
              Ø bobine estimé :{" "}
              <strong className="text-foreground">{geo.diametre_mm} mm</strong>
              {geo.epaisseur_utilisee_um != null && (
                <> · épaisseur utilisée {geo.epaisseur_utilisee_um} µm</>
              )}
            </p>
          )}
        </SectionCard>

        {/* ── Bobinage ─────────────────────────────────────────────── */}
        <SectionCard title="Bobinage">
          <div className="grid grid-cols-3 gap-3">
            <Field label="Ø mandrin (mm)">
              <Input
                type="number"
                min={10}
                value={mandrin}
                onChange={(e) => setMandrin(e.target.value)}
                data-testid="b-mandrin"
              />
            </Field>
            <Field label="Ø max bobine (mm)">
              <Input
                type="number"
                min={50}
                value={diametreMax}
                onChange={(e) => setDiametreMax(e.target.value)}
                placeholder="optionnel"
                data-testid="b-diametre-max"
              />
            </Field>
            <Field label="Sens enroulement (0-9)">
              <Input
                type="number"
                min={0}
                max={9}
                value={sens}
                onChange={(e) => setSens(e.target.value)}
                data-testid="b-sens"
              />
            </Field>
          </div>
        </SectionCard>

        {/* ── Finitions (chips) ─────────────────────────────────────── */}
        <SectionCard title="Finitions">
          {optionsDispo.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aucune option de fabrication configurée.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {optionsDispo.map((o) => {
                const actif = optionsCodes.has(o.code);
                const delta = optionByCode.get(o.code) ?? null;
                const label = coutLevier(delta);
                return (
                  <button
                    key={o.code}
                    type="button"
                    aria-pressed={actif ? "true" : "false"}
                    onClick={() => toggleOption(o.code)}
                    data-testid={`fin-${o.code}`}
                    className={
                      "rounded-full border px-3 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E85D2F]/60 " +
                      (actif
                        ? "border-[#E85D2F] bg-[#E85D2F] text-white"
                        : "border-border bg-white text-foreground hover:border-[#E85D2F]/50")
                    }
                  >
                    {o.libelle}
                    {label && (
                      <span
                        className={
                          "ml-2 text-xs " +
                          (actif ? "text-white/90" : "text-muted-foreground")
                        }
                      >
                        {label}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
          {couleurPlus && (
            <p data-testid="couleur-plus" className="text-xs text-muted-foreground">
              + 1 couleur d&apos;impression : {coutLevier(couleurPlus)}
            </p>
          )}
        </SectionCard>

        {/* ── Commercial (V0) — marge & remise live ────────────────── */}
        <SectionCard title="Commercial">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Marge (%)">
              <Input
                type="number"
                min={0}
                max={200}
                step="0.5"
                value={margePct}
                onChange={(e) => setMargePct(e.target.value)}
                placeholder={
                  preview?.marge_pct != null
                    ? `défaut ${Math.round(preview.marge_pct)}`
                    : "défaut tenant"
                }
                data-testid="c-marge"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Vide = marge par défaut de l&apos;entreprise. Bouge le prix en
                direct.
              </p>
            </Field>
            <Field label="Réduction commerciale (%)">
              <Input
                type="number"
                min={0}
                max={100}
                step="0.5"
                value={remisePct}
                onChange={(e) => setRemisePct(e.target.value)}
                data-testid="c-remise"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Remise par-dessus le HT brut, tracée à part — n&apos;entre pas
                dans le coût de revient.
              </p>
            </Field>
          </div>
        </SectionCard>

        {/* ── Décompo (lecture seule, depuis la preview) ───────────── */}
        <SectionCard title="Décompo coût & géométrie">
          {preview && geo && preview.decompo.length > 0 ? (
            <div className="space-y-3 text-sm">
              {/* Postes de coût (depuis preview.decompo). */}
              <ul className="space-y-1">
                {preview.decompo.map((l) => (
                  <li
                    key={l.poste}
                    className="flex items-baseline justify-between gap-2"
                  >
                    <span className="text-muted-foreground">{l.poste}</span>
                    <span className="font-mono">{eur(l.montant)} €</span>
                  </li>
                ))}
              </ul>
              {/* Refente (mode sans outil) — vert = ligne refente. */}
              {modeSansOutil &&
                geo.dechet_lateral_mm !== null &&
                geo.dechet_lateral_mm > 0 && (
                  <p data-testid="decompo-dechet" className="text-emerald-800">
                    Refente : déchet latéral{" "}
                    <strong>{geo.dechet_lateral_mm} mm</strong>
                    {geo.nb_filles !== null && (
                      <>
                        {" · "}
                        <strong>{geo.nb_filles}</strong> bobine(s) fille(s)
                      </>
                    )}
                  </p>
                )}
              <p className="font-mono text-xs text-muted-foreground">
                {geo.nb_poses ?? "—"} poses
                {geo.nb_filles !== null && <> · {geo.nb_filles} fille(s)</>} · Ø
                bobine ≈ {geo.diametre_mm ?? "—"} mm
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Renseigne le format et la quantité pour la décompo.
            </p>
          )}
          <p className="mt-2 text-xs text-blue-700">
            ⓘ Recalcul live via le moteur de coût (POST /api/devis/preview,
            read-only). Le devis définitif est figé à la validation.
          </p>
        </SectionCard>
          </div>
        </div>

        {/* ── Barre prix basse fixe (mobile uniquement) ────────────── */}
        <div
          data-testid="mobile-bar"
          className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-between gap-3 border-t border-border bg-white/95 px-4 py-3 shadow-[0_-2px_10px_rgba(0,0,0,0.06)] backdrop-blur lg:hidden"
        >
          <div className="min-w-0">
            {preview && preview.prix_ht !== null ? (
              <>
                <span className="text-lg font-bold text-[#E85D2F]">
                  {eur(preview.prix_ht_net ?? preview.prix_ht)} €
                </span>
                <span className="ml-1 text-xs text-muted-foreground">
                  HT · {eur(preview.prix_1000)}/1000
                  {preview.marge_pct !== null && (
                    <> · marge {Math.round(preview.marge_pct)} %</>
                  )}
                </span>
              </>
            ) : (
              <span className="text-sm text-muted-foreground">
                {recomputing ? "Calcul…" : "Renseigne format & quantité"}
              </span>
            )}
          </div>
          <Button
            type="submit"
            disabled={!peutValider || submitting}
            data-testid="valider-mobile"
            className="shrink-0 bg-[#E85D2F] px-6 text-base font-semibold text-white hover:bg-[#d24f24] disabled:opacity-50"
          >
            {submitting ? "…" : "Valider"}
          </Button>
        </div>
      </form>
    </main>
  );
}

// ── Petits composants de présentation ───────────────────────────────

/** Section repliable en transition douce (hauteur + opacité) sans mesure JS :
 * grille `grid-rows-[0fr→1fr]` + overflow caché. Le contenu reste monté (les
 * transitions enter ET exit s'animent) ; `aria-hidden` le retire de l'arbre
 * d'accessibilité, et l'appelant met ses contrôles hors tab-order (tabIndex
 * -1) à l'état fermé. `motion-reduce` respecte prefers-reduced-motion. */
function Collapsible({
  open,
  testId,
  children,
}: {
  open: boolean;
  testId?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      data-testid={testId}
      aria-hidden={!open ? "true" : undefined}
      className={
        "grid transition-all duration-300 ease-in-out motion-reduce:transition-none " +
        (open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")
      }
    >
      <div className="overflow-hidden">{children}</div>
    </div>
  );
}

function SectionCard({
  title,
  accent,
  children,
}: {
  title: string;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card className="border-border bg-white shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className={accent ? "text-base text-[#E85D2F]" : "text-base"}>
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
