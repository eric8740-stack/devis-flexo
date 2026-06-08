"use client";

/**
 * Lot front — devis en UNE page scrollable réactive (remplace à terme le
 * wizard 4 étapes). Route AUTONOME `/devis/nouvelle` : le wizard
 * (`/optimisation`, `/devis/nouveau`) reste intact tant que cette page n'est
 * pas validée en preview. Pas de big-bang.
 *
 * Réactivité : à chaque saisie (debounce 300 ms) → `previewDevisLive` (MOCK
 * du contrat `POST /api/devis/preview` tant que le back CC1 n'est pas mergé,
 * cf. devisPreviewMock.ts) → maj hero prix + décompo + indices dérivés.
 * « Valider » → `createDevis` (flux de persistance existant).
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
  listCylindres,
  listMachines,
  listMatieres,
  type CylindreParc,
  type Machine,
  type MatiereOut,
  type OptionDisponible,
} from "@/lib/api";

import {
  computeDevisPreview,
  cylindresCompatibles,
  type DevisPreviewResult,
} from "./devisPreviewMock";

// Palette FlexoSuite : accent/CTA orange #E85D2F (classes Tailwind arbitraires
// text-[#E85D2F] / bg-[#E85D2F]), gains/refente emerald, info/aide bleu, fond
// papier chaud #FBF7F0. La couleur porte du sens.

function eur(n: number): string {
  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function DevisPageUnique() {
  const router = useRouter();
  const { toast } = useToast();

  // ── Données parc (chargées au mount) ──────────────────────────────
  const [matieres, setMatieres] = useState<MatiereOut[]>([]);
  const [cylindres, setCylindres] = useState<CylindreParc[]>([]);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [optionsDispo, setOptionsDispo] = useState<OptionDisponible[]>([]);

  // ── Saisie (état local de la page) ────────────────────────────────
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
  // Matière.
  const [matiereId, setMatiereId] = useState<number | null>(null);
  const [epaisseur, setEpaisseur] = useState("150");
  // Bobinage.
  const [mandrin, setMandrin] = useState("76");
  const [diametreMax, setDiametreMax] = useState("");
  const [sens, setSens] = useState("1");
  // Finitions.
  const [optionsCodes, setOptionsCodes] = useState<Set<string>>(new Set());
  // Bord latéral (défaut entreprise, rempli au mount).
  const [bordLateral, setBordLateral] = useState("10");

  const [preview, setPreview] = useState<DevisPreviewResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [mats, cyls, machs, opts, ent] = await Promise.all([
          listMatieres(),
          listCylindres(true),
          listMachines(),
          getOptionsDisponibles(),
          getEntreprise(),
        ]);
        if (cancelled) return;
        setMatieres(mats);
        setCylindres(cyls);
        const actives = machs.filter((m) => m.actif);
        setMachines(actives);
        if (actives.length >= 1) setMachineId(actives[0]!.id);
        setOptionsDispo(opts);
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

  // ── Preview live (debounce 300 ms) ────────────────────────────────
  const previewInput = useMemo(
    () => ({
      laize_mm: parseFloat(laize) || 0,
      dev_mm: parseFloat(dev) || 0,
      quantite: parseInt(quantite, 10) || 0,
      nb_couleurs: parseInt(nbCouleurs, 10) || 0,
      mode_sans_outil: modeSansOutil,
      laize_stock_mm:
        modeSansOutil && laizeStock.trim() !== ""
          ? parseFloat(laizeStock)
          : null,
      nb_filles_force:
        modeSansOutil && nbFillesForce.trim() !== ""
          ? parseInt(nbFillesForce, 10)
          : null,
      cylindre_id: modeSansOutil ? null : cylindreId,
      cylindre_developpe_mm:
        cylindreId !== null
          ? parseFloat(
              cylindres.find((c) => c.id === cylindreId)?.developpe_mm ?? "0",
            )
          : null,
      // MatiereOut n'expose pas de prix (le prix m² vit sur le complexe côté
      // back) → mock à null = défaut 0.35 €/m² dans computeDevisPreview.
      matiere_prix_m2_eur: null,
      epaisseur_um: parseFloat(epaisseur) || null,
      mandrin_mm: parseInt(mandrin, 10) || 76,
      diametre_max_bobine_mm:
        diametreMax.trim() !== "" ? parseFloat(diametreMax) : null,
      nb_options: optionsCodes.size,
      bord_lateral_mm: parseFloat(bordLateral) || 0,
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
      cylindres,
      matiereSel,
      epaisseur,
      mandrin,
      diametreMax,
      optionsCodes,
      bordLateral,
    ],
  );

  // Premier rendu synchrone (évite un flash vide), puis debounce.
  const firstRun = useRef(true);
  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      setPreview(computeDevisPreview(previewInput));
      return;
    }
    const handle = setTimeout(() => {
      setPreview(computeDevisPreview(previewInput));
    }, 300);
    return () => clearTimeout(handle);
  }, [previewInput]);

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
    // Calcul synchrone sur les inputs courants (pas la state debouncée) pour
    // la persistance — poses dérivées du MOCK tant que /api/devis/preview
    // (CC1) n'est pas branché.
    const p = computeDevisPreview(previewInput);
    setSubmitting(true);
    try {
      const devis = await createDevis({
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
            nb_poses_dev: p.derived.nb_poses_dev,
            nb_poses_laize: p.derived.nb_poses_laize,
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

  const d = preview?.decompo;

  return (
    <main className="min-h-screen bg-[#FBF7F0]">
      <form
        onSubmit={handleSubmit}
        className="mx-auto max-w-3xl space-y-5 p-4 sm:p-6"
      >
        {/* ── Hero prix (sticky) — recalculé en direct ─────────────── */}
        <div
          data-testid="hero-prix"
          className="sticky top-2 z-10 rounded-xl border border-[#E85D2F]/30 bg-white/95 p-5 shadow-md backdrop-blur"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Prix de vente estimé (HT)
          </p>
          {preview?.incomplet ? (
            <p
              data-testid="hero-incomplet"
              className="mt-1 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800"
            >
              ⓘ {preview.incomplet}
            </p>
          ) : (
            <div className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <span
                data-testid="hero-prix-valeur"
                className="text-3xl font-bold text-[#E85D2F]"
              >
                {eur(preview?.prix_total_ht_eur ?? 0)} €
              </span>
              <span
                data-testid="hero-marge"
                className="rounded bg-emerald-100 px-2 py-0.5 text-sm font-semibold text-emerald-800"
              >
                marge {Math.round((preview?.marge_pct ?? 0) * 100)} %
              </span>
              <span className="text-xs text-muted-foreground">
                revient {eur(preview?.cout_revient_eur ?? 0)} € · estimation
                live
              </span>
            </div>
          )}
        </div>

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
            {modeSansOutil && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <Field label="Laize bobine stock (mm) *">
                  <Input
                    type="number"
                    min={1}
                    step="0.1"
                    value={laizeStock}
                    onChange={(e) => setLaizeStock(e.target.value)}
                    data-testid="laize-stock"
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
                  />
                </Field>
              </div>
            )}
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

        {/* ── Outil ────────────────────────────────────────────────── */}
        {!modeSansOutil && (
          <SectionCard title="Outil de découpe">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Machine">
                <select
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={machineId ?? ""}
                  onChange={(e) => setMachineId(Number(e.target.value) || null)}
                  data-testid="o-machine"
                  aria-label="Machine"
                >
                  {machines.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.nom}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Cylindre compatible">
                <select
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={cylindreId ?? ""}
                  onChange={(e) => setCylindreId(Number(e.target.value) || null)}
                  data-testid="o-cylindre"
                  aria-label="Cylindre compatible"
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
            <p className="text-xs text-muted-foreground">
              {cylindresOk.length} cylindre(s) compatible(s) avec ce développé.
              L&apos;optimisation automatique (choix malin du cylindre) arrive
              au lot suivant.
            </p>
          </SectionCard>
        )}

        {/* ── Matière ──────────────────────────────────────────────── */}
        <SectionCard title="Matière">
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
            </Field>
          </div>
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

        {/* ── Finitions ────────────────────────────────────────────── */}
        <SectionCard title="Finitions">
          {optionsDispo.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aucune option de fabrication configurée.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {optionsDispo.map((o) => (
                <label
                  key={o.code}
                  className="flex cursor-pointer items-center gap-2 rounded-md border border-border p-2 text-sm"
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[#E85D2F]"
                    checked={optionsCodes.has(o.code)}
                    onChange={() => toggleOption(o.code)}
                    data-testid={`fin-${o.code}`}
                  />
                  {o.libelle}
                </label>
              ))}
            </div>
          )}
        </SectionCard>

        {/* ── Décompo (lecture seule, depuis la preview) ───────────── */}
        <SectionCard title="Décompo laize & bobine">
          {d ? (
            <div className="space-y-1 font-mono text-sm">
              <div>
                Imprimé <strong>{d.laize_plaque_mm} mm</strong> + 2 × bord{" "}
                <strong>{d.bord_lateral_mm} mm</strong> ={" "}
                <strong>{d.laize_papier_mm} mm</strong> de laize papier
              </div>
              {d.dechet_lateral_mm != null && (
                <div data-testid="decompo-dechet" className="text-emerald-800">
                  Refente : stock <strong>{d.laize_stock_mm} mm</strong> − utile{" "}
                  <strong>{d.laize_utile_mm} mm</strong> = déchet latéral{" "}
                  <strong>{d.dechet_lateral_mm} mm</strong> ·{" "}
                  <strong>{d.nb_filles}</strong> bobine(s) fille(s)
                </div>
              )}
              <div className="text-muted-foreground">
                {preview?.derived.nb_poses_laize}×
                {preview?.derived.nb_poses_dev} poses · Ø bobine ≈{" "}
                {preview?.derived.diametre_bobine_mm} mm ·{" "}
                {preview?.derived.ml_total} ml
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">—</p>
          )}
          <p className="mt-2 text-xs text-blue-700">
            ⓘ Estimation live (contrat preview mocké tant que l&apos;endpoint
            backend n&apos;est pas déployé). Les chiffres définitifs viennent du
            moteur de coût à la validation.
          </p>
        </SectionCard>

        {/* ── Valider ──────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-8">
          <p className="text-sm text-muted-foreground">
            {peutValider
              ? "Prêt à créer le devis."
              : "Renseigne format, quantité, matière" +
                (modeSansOutil ? "." : ", machine et cylindre.")}
          </p>
          <Button
            type="submit"
            size="lg"
            disabled={!peutValider || submitting}
            data-testid="valider"
            className="bg-[#E85D2F] px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:bg-[#d24f24] disabled:opacity-50"
          >
            {submitting ? "Création…" : "Valider le devis"}
          </Button>
        </div>
      </form>
    </main>
  );
}

// ── Petits composants de présentation ───────────────────────────────

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
