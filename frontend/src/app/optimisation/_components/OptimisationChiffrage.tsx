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
  applyRebobinageDevis,
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

import { briefClientToPayload } from "./brief-client/store-helpers";
import { useClientsListe } from "./useClientsListe";
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
    nbCouleursImpression,
    goRebobinage,
    rebobinageRequest,
    optionsCodes,
    toggleOption,
    margeOverridePct,
    setMargeOverridePct,
    reductionPct,
    setReductionPct,
    devisExistantId,
    devisExistantNumero,
    briefClient,
    clientSelectionne,
    setClientSelectionne,
    sensEnroulementClient,
    diametreEchoesParLot,
  } = useOptimisationPose();
  const { toast } = useToast();
  const router = useRouter();
  // Sprint 16 auto-fill — liste partagée (cache module) avec
  // OptimisationRebobinage. Pas de double fetch.
  const { clients, loading: clientsLoading } = useClientsListe();

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
      // Sprint 16 auto-fill — sens enroulement profil propagé pour
      // traçabilité (entier 1..8 ou null). Non consommé par
      // /api/rebobinage/calculer (contrat backend inchangé) ; le
      // backend accepte les clés inconnues dans payload_input (dict
      // Pydantic non typé, cf. DevisCreate schemas/devis_persist.py).
      sens_enroulement: sensEnroulementClient,
      // Fix couleurs — compteurs de couleurs consommés par le Poste 2
      // Encres (fix backend CC1). Seul `impression` provient du store
      // (saisie étape 1) ; pantone/blanc/vernis ne sont pas encore saisis
      // dans le workflow optim → 0. Envoyé identique sur preview + POST.
      nb_couleurs: {
        impression: nbCouleursImpression,
        pantone: 0,
        blanc: 0,
        vernis: 0,
      },
    };
  }, [
    selection,
    laizeEtiqMm,
    devEtiqMm,
    mandrinMm,
    optionsCodes,
    margeOverridePct,
    sensEnroulementClient,
    nbCouleursImpression,
  ]);

  const lotsPayload = useMemo<LotProductionCreatePayload[]>(
    () =>
      selection.map((s) => {
        // Bug #6 (6.2c) — si l'étape Rebobinage a produit un écho multi-lots
        // pour ce lot, on enrichit le snapshot candidat avec le Ø RÉEL
        // (épaisseur matière du lot + paroi). `diametre_bobine_mm` est écrasé
        // → la VUE B/C + le plan bobines du rapport refléteront ce Ø. Sinon,
        // candidat brut (fallback non-régressif : devis hors flux rebobinage).
        const echo = diametreEchoesParLot[s.id_candidat];
        const payloadVisuel = echo
          ? {
              ...s.candidat,
              diametre_bobine_mm: echo.diametre_bobine_mm,
              diametre_depart_mm: echo.diametre_depart_mm,
              epaisseur_effective_um: echo.epaisseur_effective_um,
              epaisseur_source: echo.epaisseur_source,
              paroi_mm: echo.paroi_mm,
              nb_bobines_rebobinage: echo.nb_bobines,
            }
          : s.candidat;
        return {
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
          // SchemaImplantation côté UI sans recalcul moteur. Enrichi du Ø réel
          // par lot quand un écho rebobinage existe (bug #6 6.2c).
          payload_visuel: payloadVisuel as unknown as Record<string, unknown>,
        };
      }),
    [selection, diametreEchoesParLot]
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

      // Sprint 14 Lot 4.4 — projection des 5 champs brief client vers le
      // shape DevisCreate/DevisUpdate (gère null → omis sur sous-stockage).
      const briefPayload = briefClientToPayload(briefClient);

      let devisId: number;
      let devisNumero: string;

      // Sprint 16 auto-fill — client_id propagé depuis le store
      // (alimenté par le sélecteur en tête de l'étape rebobinage et/ou
      // de cette étape chiffrage — source de vérité unique).
      const clientIdPayload = clientSelectionne?.id ?? null;

      if (enModeEdition && devisExistantId !== null) {
        const updatePayload: DevisUpdate = {
          payload_input: payloadInput,
          payload_output: payloadOutput,
          quantite_totale: quantiteTotale,
          lots: lotsPayload,
          reduction_pct: reductionValide ? reductionNum : 0,
          client_id: clientIdPayload,
          ...briefPayload,
        };
        const devis = await updateDevis(devisExistantId, updatePayload);
        devisId = devis.id;
        devisNumero = devis.numero;
        toast({
          title: "Devis mis à jour ✓",
          description: `Devis ${devis.numero} mis à jour — direction ta page détail.`,
        });
      } else {
        const createPayload: DevisCreate = {
          payload_input: payloadInput,
          payload_output: payloadOutput,
          statut: "brouillon",
          quantite_totale: quantiteTotale,
          lots: lotsPayload,
          client_id: clientIdPayload,
          ...briefPayload,
        };
        const devis = await createDevis(createPayload);
        devisId = devis.id;
        devisNumero = devis.numero;
        toast({
          title: "Devis créé ✓",
          description: `Devis ${devis.numero} créé avec ${selection.length} lot(s).`,
        });
      }

      // Sprint 16 Lot D — applique la ligne rebobinage sur le devis si
      // l'étape rebobinage a propagé un request au store. Échec ici ≠
      // échec du devis : on log un warning sans bloquer la navigation,
      // l'opérateur pourra ré-appliquer plus tard depuis la fiche devis.
      if (rebobinageRequest !== null) {
        try {
          await applyRebobinageDevis(devisId, rebobinageRequest);
        } catch (rebobErr) {
          toast({
            title: "Rebobinage non appliqué",
            description:
              rebobErr instanceof Error
                ? `Devis ${devisNumero} créé/mis à jour mais la ligne rebobinage a échoué : ${rebobErr.message}`
                : "Devis créé/mis à jour mais la ligne rebobinage a échoué.",
            variant: "destructive",
          });
        }
      }

      router.push(`/devis/${devisId}`);
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
    <section className="mx-auto max-w-6xl space-y-5 p-6">
      {enModeEdition && devisExistantNumero && (
        <div className="rounded-lg border-l-4 border-l-amber-500 bg-gradient-to-r from-amber-50 via-amber-50/80 to-white px-4 py-3 text-sm text-amber-900 shadow-sm">
          <strong>✎ Édition du devis {devisExistantNumero}</strong> — tu
          modifies un devis existant. À la validation, je remplace tes
          lots et recalcule le chiffrage en gardant le même numéro.
        </div>
      )}

      {/* Stepper visuel 4/4 — pos brief #33 §9bis (design joyeux). */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800">
          ✓ Saisie
        </span>
        <span className="text-muted-foreground">›</span>
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800">
          ✓ Candidats
        </span>
        <span className="text-muted-foreground">›</span>
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800">
          ✓ Lots & matières
        </span>
        <span className="text-muted-foreground">›</span>
        <span className="rounded-full bg-gradient-to-r from-blue-700 to-amber-600 px-3 py-0.5 font-semibold text-white shadow-sm">
          ④ Chiffrage
        </span>
      </div>

      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2
            className="bg-gradient-to-r from-blue-800 to-amber-700 bg-clip-text text-3xl font-bold text-transparent"
            style={{ fontFamily: "Fraunces, serif" }}
          >
            💰 Chiffrage final
          </h2>
          <p className="text-sm text-muted-foreground">
            Ajuste tes options globales, ta marge et ta réduction
            commerciale. Le récap brut/net se rafraîchit tout seul à
            chaque clic — pas besoin de revalider.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={goRebobinage}>
          ← Retour rebobinage
        </Button>
      </header>

      {/* Sprint 16 auto-fill — sélecteur client synchronisé avec
          l'étape rebobinage via le store (source de vérité unique).
          Affiché ici aussi pour permettre une dernière correction
          avant POST/PUT devis. */}
      <Card data-testid="chiffrage-client-section">
        <CardHeader>
          <CardTitle>Client du devis</CardTitle>
          <CardDescription>
            Synchronisé avec le sélecteur de l&apos;étape rebobinage —
            un seul client, deux points d&apos;accès.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {clientsLoading ? (
            <p className="text-sm text-muted-foreground">
              Chargement des clients…
            </p>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="chiffrage-client">Client</Label>
              <select
                id="chiffrage-client"
                data-testid="chiffrage-client-select"
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={clientSelectionne?.id ?? ""}
                onChange={(e) => {
                  const id = e.target.value
                    ? Number(e.target.value)
                    : null;
                  const next = id !== null
                    ? clients.find((c) => c.id === id) ?? null
                    : null;
                  setClientSelectionne(next);
                }}
              >
                <option value="">— Aucun client sélectionné —</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.raison_sociale}
                  </option>
                ))}
              </select>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* --- Options de fabrication globales --- */}
        <Card className="border-l-4 border-l-blue-500 lg:col-span-2">
          <CardHeader>
            <CardTitle>⚙ Options de fabrication globales</CardTitle>
            <CardDescription>
              Coche celles qui s&apos;appliquent au devis entier (tous les
              lots). Le moteur consommera ces codes à la prochaine itération
              — pour l&apos;instant je les snapshote dans le payload pour la
              traçabilité.
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
            <CardTitle>📈 Marge override</CardTitle>
            <CardDescription>
              Optionnel — surcharge la marge du barème pour ce devis. Laisse
              vide si la marge par défaut te convient.
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
              className="text-lg font-semibold"
            />
            <p className="text-xs text-muted-foreground">
              Typique flexo étiquettes : 30-60 %.
            </p>
          </CardContent>
        </Card>

        {/* --- Réduction commerciale --- */}
        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader>
            <CardTitle>🎁 Réduction commerciale</CardTitle>
            <CardDescription>
              La remise que tu accordes au client par-dessus le brut. Stockée
              à part pour qu&apos;elle reste traçable côté commercial.
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
              className="text-lg font-semibold"
            />
            <p className="text-xs text-muted-foreground">
              0 % = pas de remise. 100 % max.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* --- Récap hero gradient bleu→or (§9bis brief #33) --- */}
      <div className="relative overflow-hidden rounded-2xl border-2 border-blue-300 bg-gradient-to-br from-blue-100/70 via-white to-amber-100/70 p-8 shadow-lg">
        <div className="absolute right-4 top-3 text-[10px] uppercase tracking-widest text-muted-foreground">
          💡 Recalcul live
        </div>
        <p className="mb-4 text-center text-xs uppercase tracking-widest text-muted-foreground">
          {selection.length} lot{selection.length > 1 ? "s" : ""} ·{" "}
          {quantiteTotale.toLocaleString("fr-FR")} étiquettes au total
        </p>
        {/* Fix bandeau erreur chiffrage — si le backend signale un chiffrage
            incomplet (chiffrage_auto_erreur), on n'affiche AUCUN prix (pas de
            « 0,00 € » trompeur) : on remplace tout le bloc par un bandeau
            d'erreur explicite. Sinon, récap brut / réduction / net habituel. */}
        {preview?.chiffrage_auto_erreur ? (
          <div
            role="alert"
            data-testid="chiffrage-erreur-bandeau"
            className="rounded-xl border-2 border-red-300 bg-red-50 px-5 py-4 text-red-900"
          >
            <p className="text-base font-semibold">
              ⚠ Chiffrage incomplet — aucun prix calculé
            </p>
            <p className="mt-1 text-sm">{preview.chiffrage_auto_erreur}</p>
            <p className="mt-2 text-xs text-red-700">
              Corrige la cause ci-dessus puis recalcule. Tant que le chiffrage
              n&apos;aboutit pas, le devis ne porte pas de prix valide.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="text-center">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Coût brut HT
              </p>
              <p
                className="mt-1 text-2xl font-bold text-blue-900"
                style={{ fontFamily: "Fraunces, serif" }}
              >
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
              <p
                className="mt-1 text-2xl font-bold text-emerald-700"
                style={{ fontFamily: "Fraunces, serif" }}
              >
                {previewLoading
                  ? "…"
                  : preview
                    ? `−${formaterEuros(preview.reduction_eur)} €`
                    : "—"}
              </p>
              <p className="text-xs text-muted-foreground">
                {preview ? `${formaterEuros(preview.reduction_pct)} %` : ""}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Coût net HT
              </p>
              <p
                className="mt-1 bg-gradient-to-r from-blue-700 to-amber-700 bg-clip-text text-4xl font-extrabold text-transparent"
                style={{ fontFamily: "Fraunces, serif" }}
              >
                {previewLoading
                  ? "…"
                  : preview
                    ? `${formaterEuros(preview.cout_net_ht_eur)} €`
                    : "—"}
              </p>
            </div>
          </div>
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
        {!enModeEdition && (
          <p className="mt-3 text-center text-xs text-muted-foreground">
            Une fois validé, je te redirige sur la page détail pour
            l&apos;imprimer, le dupliquer ou repartir d&apos;ici.
          </p>
        )}
      </div>
    </section>
  );
}
