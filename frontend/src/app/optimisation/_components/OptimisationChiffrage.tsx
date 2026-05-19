"use client";

/**
 * Étape 4 — Chiffrage final (Brief #33).
 *
 * Options globales (catalogue tenant), marge override, réduction
 * commerciale. Récap brut/net live via /api/devis/preview-couts.
 * POST /api/devis en mode création OU PUT /api/devis/{id} en mode
 * édition (selon `devisExistantId` du store, alimenté par commit 3).
 *
 * Le débit de la marge override pilote `payload_input.pct_marge_override`
 * (champ Sprint 5 du cost_engine). Les options codes sont snapshotées
 * dans `payload_input.options_codes_etape4` pour traçabilité (limitation
 * acceptée commit 1 : pas encore consommé par cost_engine).
 */
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  createDevis,
  getOptionsDisponibles,
  previewCoutsDevis,
  updateDevis,
  type DevisCreate,
  type DevisUpdate,
  type LotProductionCreatePayload,
  type OptionDisponible,
  type PreviewCoutsResponse,
} from "@/lib/api";

import { useOptimisationPose } from "./OptimisationPoseStore";

function sensEnroulementToInt(se: string): number {
  return parseInt(se.replace("SE", ""), 10);
}

function formaterEuros(montantStr: string | number | undefined): string {
  if (montantStr === undefined || montantStr === null) return "—";
  const n = typeof montantStr === "string" ? parseFloat(montantStr) : montantStr;
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function OptimisationChiffrage() {
  const {
    selection,
    quantiteTotale,
    laizeEtiqMm,
    devEtiqMm,
    mandrinMm,
    goDetail,
    optionsCodes,
    toggleOption,
    margeOverridePct,
    setMargeOverridePct,
    reductionPct,
    setReductionPct,
    devisExistantId,
    devisExistantNumero,
  } = useOptimisationPose();
  const { toast } = useToast();
  const router = useRouter();

  const enModeEdition = devisExistantId !== null;

  const [options, setOptions] = useState<OptionDisponible[] | null>(null);
  const [preview, setPreview] = useState<PreviewCoutsResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Chargement options catalogue tenant (one-shot).
  useEffect(() => {
    let cancelled = false;
    getOptionsDisponibles()
      .then((opts) => {
        if (!cancelled) setOptions(opts);
      })
      .catch((err) => {
        toast({
          title: "Chargement options impossible",
          description: err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [toast]);

  const optionsByCategorie = useMemo(() => {
    if (!options) return {};
    const out: Record<string, OptionDisponible[]> = {};
    for (const o of options) {
      const cat = o.categorie ?? "Autres";
      if (!out[cat]) out[cat] = [];
      out[cat].push(o);
    }
    return out;
  }, [options]);

  // Construction du payload_input commun (utilisé pour preview et persistence).
  const payloadInput = useMemo(() => {
    const premierLot = selection[0]?.candidat;
    const margeNum = parseFloat(margeOverridePct);
    return {
      machine_id: premierLot?.machine_id ?? null,
      format_etiquette_largeur_mm: laizeEtiqMm,
      format_etiquette_hauteur_mm: devEtiqMm,
      mode_calcul: "manuel",
      source: "optim_multi_lots",
      nb_lots: selection.length,
      mandrin_mm: mandrinMm,
      options_codes_etape4: optionsCodes,
      pct_marge_override:
        margeOverridePct.trim() !== "" && !Number.isNaN(margeNum)
          ? margeNum
          : null,
    };
  }, [
    selection,
    laizeEtiqMm,
    devEtiqMm,
    mandrinMm,
    optionsCodes,
    margeOverridePct,
  ]);

  const lotsPayload = useMemo<LotProductionCreatePayload[]>(
    () =>
      selection.map((s) => ({
        cylindre_id: s.candidat.cylindre_id,
        machine_id: s.candidat.machine_id,
        nb_poses_dev: s.candidat.nb_poses_dev,
        nb_poses_laize: s.candidat.nb_poses_laize,
        sens_enroulement: sensEnroulementToInt(s.candidat.sens_enroulement),
        quantite: s.quantite,
        matiere_id: s.matiere_id as number,
        intervalle_dev_reel_mm: String(s.candidat.intervalle_dev_reel_mm),
        intervalle_laize_reel_mm: String(s.candidat.intervalle_laize_reel_mm),
        largeur_plaque_mm: String(s.candidat.largeur_plaque_mm),
        score_optim: s.candidat.score,
        // Brief #33 commit 5 — snapshot complet du candidat pour rejouer
        // SchemaImplantation côté UI sans recalcul moteur.
        payload_visuel: s.candidat as unknown as Record<string, unknown>,
      })),
    [selection]
  );

  // Debounced preview-couts à chaque changement options/marge/réduction.
  useEffect(() => {
    if (selection.length === 0) return;
    const reductionNum = parseFloat(reductionPct);
    const reductionValide =
      reductionPct.trim() !== "" && !Number.isNaN(reductionNum);
    const handle = setTimeout(() => {
      setPreviewLoading(true);
      previewCoutsDevis({
        payload_input: payloadInput,
        lots: lotsPayload,
        reduction_pct: reductionValide ? reductionNum : 0,
      })
        .then((res) => {
          setPreview(res);
        })
        .catch((err) => {
          toast({
            title: "Recalcul impossible",
            description:
              err instanceof Error ? err.message : "Erreur inconnue",
            variant: "destructive",
          });
        })
        .finally(() => setPreviewLoading(false));
    }, 400);
    return () => clearTimeout(handle);
  }, [payloadInput, lotsPayload, reductionPct, selection.length, toast]);

  const handleSubmit = async () => {
    if (selection.length === 0) return;
    setSubmitting(true);
    try {
      const coutBrut = preview?.cout_brut_ht_eur ?? "0.00";
      const reductionNum = parseFloat(reductionPct);
      const reductionValide =
        reductionPct.trim() !== "" && !Number.isNaN(reductionNum);

      const payloadOutput = {
        mode: "manuel",
        prix_vente_ht_eur: coutBrut,
        cout_brut_ht_eur: preview?.cout_brut_ht_eur ?? null,
        cout_net_ht_eur: preview?.cout_net_ht_eur ?? null,
        reduction_pct: preview?.reduction_pct ?? "0",
        nb_lots: selection.length,
      };

      if (enModeEdition && devisExistantId !== null) {
        const updatePayload: DevisUpdate = {
          payload_input: payloadInput,
          payload_output: payloadOutput,
          quantite_totale: quantiteTotale,
          lots: lotsPayload,
          reduction_pct: reductionValide ? reductionNum : 0,
        };
        const devis = await updateDevis(devisExistantId, updatePayload);
        toast({
          title: "Devis mis à jour ✓",
          description: `Devis ${devis.numero} mis à jour — direction ta page détail.`,
        });
        router.push(`/devis/${devis.id}`);
      } else {
        const createPayload: DevisCreate = {
          payload_input: payloadInput,
          payload_output: payloadOutput,
          statut: "brouillon",
          quantite_totale: quantiteTotale,
          lots: lotsPayload,
        };
        const devis = await createDevis(createPayload);
        toast({
          title: "Devis créé ✓",
          description: `Devis ${devis.numero} créé avec ${selection.length} lot(s).`,
        });
        router.push(`/devis/${devis.id}`);
      }
    } catch (err) {
      toast({
        title: enModeEdition
          ? "Mise à jour impossible"
          : "Création du devis impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="space-y-5">
      {enModeEdition && devisExistantNumero && (
        <div className="rounded-lg border-l-4 border-l-amber-500 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-sm">
          <strong>Édition du devis {devisExistantNumero}</strong> — tu
          modifies un devis existant. La validation finale fera un
          <em> PUT</em> qui remplace les lots et recalcule le chiffrage.
        </div>
      )}
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">
            Étape 4 — Chiffrage{" "}
            {enModeEdition && devisExistantNumero
              ? `· édition ${devisExistantNumero}`
              : ""}
          </h2>
          <p className="text-sm text-muted-foreground">
            Ajuste les options globales, la marge et la réduction
            commerciale. Le récap brut/net se recalcule en direct.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={goDetail}>
          ← Retour détail lots
        </Button>
      </header>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* --- Options de fabrication globales --- */}
        <Card className="border-l-4 border-l-blue-500 lg:col-span-2">
          <CardHeader>
            <CardTitle>Options de fabrication globales</CardTitle>
            <CardDescription>
              Cochées au niveau devis (s&apos;appliquent à tous les lots). Le
              chiffrage moteur consommera les codes au prochain itération —
              elles sont snapshotées dans le payload pour traçabilité.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {options === null && (
              <p className="text-sm text-muted-foreground">Chargement…</p>
            )}
            {options !== null && options.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Aucune option configurée dans le catalogue tenant.
              </p>
            )}
            {options !== null &&
              options.length > 0 &&
              Object.entries(optionsByCategorie).map(([cat, opts]) => (
                <section key={cat}>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {cat}
                  </h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {opts.map((o) => (
                      <label
                        key={o.code}
                        htmlFor={`opt-chiffrage-${o.code}`}
                        className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-2 text-sm hover:bg-muted/50"
                      >
                        <input
                          id={`opt-chiffrage-${o.code}`}
                          type="checkbox"
                          checked={optionsCodes.includes(o.code)}
                          onChange={() => toggleOption(o.code)}
                          className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
                        />
                        <div className="flex-1">
                          <div className="font-medium">{o.libelle}</div>
                          <div className="text-xs text-muted-foreground">
                            vit ×{o.coef_vitesse_impact} · gâche ×
                            {o.coef_gache_impact}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </section>
              ))}
          </CardContent>
        </Card>

        {/* --- Marge override --- */}
        <Card className="border-l-4 border-l-amber-500">
          <CardHeader>
            <CardTitle>Marge override</CardTitle>
            <CardDescription>
              Optionnel — surcharge le % de marge appliqué par le moteur de
              chiffrage. Laisse vide pour conserver la marge par défaut du
              barème.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="marge-override">Marge (%)</Label>
            <Input
              id="marge-override"
              type="number"
              step="0.1"
              min={0}
              max={500}
              placeholder="(défaut barème)"
              value={margeOverridePct}
              onChange={(e) => setMargeOverridePct(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Valeur typique 30-60 % flexo étiquettes.
            </p>
          </CardContent>
        </Card>

        {/* --- Réduction commerciale --- */}
        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader>
            <CardTitle>Réduction commerciale</CardTitle>
            <CardDescription>
              Remise appliquée sur le total brut. Stockée séparément du
              moteur de chiffrage pour traçabilité commerciale.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="reduction">Réduction (%)</Label>
            <Input
              id="reduction"
              type="number"
              step="0.1"
              min={0}
              max={100}
              value={reductionPct}
              onChange={(e) => setReductionPct(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              0 % = aucune remise. 100 % max.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* --- Récap hero gradient bleu→or --- */}
      <div className="rounded-lg border-2 border-blue-300 bg-gradient-to-br from-blue-100/60 via-white to-amber-100/60 p-6 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="text-center">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Coût brut HT
            </p>
            <p className="mt-1 text-2xl font-bold text-blue-900">
              {previewLoading
                ? "…"
                : preview
                  ? `${formaterEuros(preview.cout_brut_ht_eur)} €`
                  : "—"}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Réduction
            </p>
            <p className="mt-1 text-2xl font-bold text-emerald-700">
              {previewLoading
                ? "…"
                : preview
                  ? `−${formaterEuros(preview.reduction_eur)} €`
                  : "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              {preview
                ? `${formaterEuros(preview.reduction_pct)} %`
                : ""}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Coût net HT
            </p>
            <p className="mt-1 bg-gradient-to-r from-blue-700 to-amber-700 bg-clip-text text-3xl font-extrabold text-transparent">
              {previewLoading
                ? "…"
                : preview
                  ? `${formaterEuros(preview.cout_net_ht_eur)} €`
                  : "—"}
            </p>
          </div>
        </div>

        {preview?.chiffrage_erreur && (
          <p className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-center text-sm text-amber-800">
            ⚠ Chiffrage auto en mode dégradé : {preview.chiffrage_erreur}
          </p>
        )}

        <div className="mt-6 flex justify-center">
          <Button
            size="lg"
            onClick={handleSubmit}
            disabled={submitting || selection.length === 0}
            className="bg-gradient-to-r from-blue-700 to-amber-600 px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:from-blue-800 hover:to-amber-700 hover:shadow-lg disabled:from-gray-300 disabled:to-gray-400 disabled:shadow-none"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg
                  className="h-4 w-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="3"
                    className="opacity-25"
                  />
                  <path
                    d="M4 12a8 8 0 018-8"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                  />
                </svg>
                {enModeEdition ? "Mise à jour en cours…" : "Création en cours…"}
              </span>
            ) : enModeEdition ? (
              <>✓ Mettre à jour le devis</>
            ) : (
              <>✓ Créer le devis</>
            )}
          </Button>
        </div>
      </div>
    </section>
  );
}
