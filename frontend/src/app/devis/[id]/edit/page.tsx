"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DevisCalculForm } from "@/components/DevisCalculForm";
import { DevisResult } from "@/components/DevisResult";
import { DevisSaveBar } from "@/components/DevisSaveBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  getDevisDetail,
  updateDevis,
  type DevisCalculResult,
  type DevisDetail,
  type DevisInput,
} from "@/lib/api";
import {
  briefClientEstVide,
  formatLieu,
  formatMmOrTiret,
  formatNbOrTiret,
  formatPourcentOrTiret,
  formatTemperatureOrTiret,
  formatTypeEntree,
  NON_RENSEIGNE,
} from "@/lib/brief-client-display";

export default function EditDevisPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);

  const [devis, setDevis] = useState<DevisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DevisCalculResult | null>(null);
  const [input, setInput] = useState<DevisInput | null>(null);

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError("ID de devis invalide");
      return;
    }
    getDevisDetail(id)
      .then(setDevis)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  if (error) {
    return (
      <main className="container mx-auto max-w-5xl p-4 sm:p-8">
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive"
        >
          <strong>Erreur :</strong> {error}
        </div>
        <div className="mt-4">
          <Button asChild variant="outline">
            <Link href="/devis">↩ Retour à la liste</Link>
          </Button>
        </div>
      </main>
    );
  }

  if (!devis) {
    return (
      <main className="container mx-auto max-w-5xl p-4 sm:p-8">
        <div className="text-sm text-muted-foreground">Chargement…</div>
      </main>
    );
  }

  // Brief #32 commit 5 (réduit) — détection mode multi-lots : si présent,
  // on bascule sur un panneau dédié read-only sur les lots + édition
  // `reduction_pct` uniquement. L'édition complète des lots (changer
  // cylindre/poses/matière) reste TODO d'un brief futur.
  const isMultiLots =
    (devis.lots_production?.length ?? 0) > 0 ||
    (devis.payload_output as Record<string, unknown>)?.mode === "multi-lots";

  if (isMultiLots) {
    return <EditMultiLotsPanel devis={devis} onSaved={() => router.push(`/devis/${devis.id}`)} />;
  }

  const initialPayloadInput = devis.payload_input as unknown as DevisInput;

  return (
    <main className="container mx-auto max-w-5xl p-4 sm:p-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold font-mono">
            Modifier {devis.numero}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Recalculez puis sauvegardez pour mettre à jour ce devis.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/devis/${devis.id}`}>↩ Annuler</Link>
        </Button>
      </header>

      <DevisCalculForm
        initialPayloadInput={initialPayloadInput}
        onResult={(r, i) => {
          setResult(r);
          setInput(i ?? null);
        }}
      />

      {result && (
        <section className="mt-8 grid gap-6">
          <DevisResult data={result} />
          {input && (
            <DevisSaveBar
              input={input}
              result={result}
              mode="edit"
              devisId={devis.id}
              initialClientId={devis.client_id}
              initialStatut={devis.statut}
              initialCylindreZ={devis.cylindre_choisi_z}
              initialCylindreNbEtiq={devis.cylindre_choisi_nb_etiq}
              onSaved={(savedId) => router.push(`/devis/${savedId}`)}
            />
          )}
        </section>
      )}
    </main>
  );
}


/**
 * Brief #32 commit 5 (réduit) — édition devis multi-lots.
 *
 * Scope minimal : affichage read-only des lots existants + édition de la
 * réduction commerciale (%). L'édition complète des lots (changer cyl,
 * machine, poses, matière par lot) est volontairement hors scope brief
 * #32 et fera l'objet d'un brief futur dédié — gros chantier UX qui
 * nécessite un workflow pas-à-pas (étape 2 candidats à re-jouer avec
 * pré-sélection, etc.).
 *
 * Design joyeux conforme §9bis : header gradient bleu→ambre, slider
 * coloré, bouton primary rempli, microcopie tutoyée.
 */
function EditMultiLotsPanel({
  devis,
  onSaved,
}: {
  devis: DevisDetail;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const lots = devis.lots_production ?? [];
  const initialReduction = parseFloat(devis.reduction_pct ?? "0") || 0;
  const [reductionPct, setReductionPct] = useState<number>(initialReduction);
  const [saving, setSaving] = useState(false);

  const brut = parseFloat(devis.ht_total_eur) || 0;
  const apresRemise = brut * (1 - reductionPct / 100);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateDevis(devis.id, { reduction_pct: reductionPct });
      toast({
        title: "Devis modifié ✓",
        description: `Réduction ${reductionPct.toFixed(2)}% appliquée à ${devis.numero}.`,
      });
      onSaved();
    } catch (err) {
      toast({
        title: "Modification impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="container mx-auto max-w-4xl space-y-6 p-4 sm:p-8">
      <header className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50/60 via-amber-50/30 to-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1
              className="bg-gradient-to-r from-blue-800 to-amber-700 bg-clip-text font-mono text-2xl font-bold text-transparent"
              style={{ fontFamily: "Fraunces, serif" }}
            >
              ✎ Modifie {devis.numero}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Ajuste ta réduction commerciale. L&apos;édition complète des
              lots arrive bientôt — pour l&apos;instant ils restent figés.
            </p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href={`/devis/${devis.id}`}>↩ Annuler</Link>
          </Button>
        </div>
      </header>

      {/* Rappel des lots — read-only */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Tes lots de production · figés
        </h2>
        {lots.map((lot) => (
          <div
            key={lot.id}
            className="rounded-lg border-l-4 border-l-blue-700 border-y border-r border-y-border border-r-border bg-white p-4 text-sm"
          >
            <strong>Lot {lot.ordre}</strong> · {lot.cylindre_nb_dents ?? "?"} dents
            · {lot.machine_nom} · {lot.nb_poses_laize}×{lot.nb_poses_dev} poses
            · {lot.quantite.toLocaleString("fr-FR")} étiquettes ·{" "}
            {lot.matiere_libelle ?? `#${lot.matiere_id}`}
            {lot.cout_lot_ht_eur && (
              <span className="ml-2 font-mono text-blue-800">
                {parseFloat(lot.cout_lot_ht_eur).toFixed(2)} €
              </span>
            )}
          </div>
        ))}
      </section>

      {/* Sprint 14 Lot 4.6 — Brief client (lecture seule). Édition reportée
          S15+. Affiche les 5 champs persistés au moment du devis. */}
      <BriefClientReadOnly devis={devis} />

      {/* Édition réduction */}
      <section className="rounded-xl border-2 border-blue-200 bg-gradient-to-br from-blue-50 via-amber-50/50 to-white p-6 shadow">
        <div className="space-y-4">
          <div>
            <Label htmlFor="reduction" className="text-base">
              Réduction commerciale (%)
            </Label>
            <p className="text-xs text-muted-foreground">
              Une remise globale appliquée par-dessus le coût calculé.
              Reste à 0 si tu n&apos;en accordes pas.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Input
              id="reduction"
              type="number"
              min={0}
              max={100}
              step={0.5}
              value={reductionPct}
              onChange={(e) => setReductionPct(parseFloat(e.target.value) || 0)}
              className="w-32"
            />
            <span className="text-sm text-muted-foreground">%</span>
          </div>

          <div className="rounded bg-white/60 p-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">Brut HT :</span>{" "}
                <strong className="font-mono">
                  {brut.toLocaleString("fr-FR", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}{" "}
                  €
                </strong>
              </div>
              <div className="text-right">
                <span className="text-muted-foreground">
                  Après réduction {reductionPct}% :
                </span>{" "}
                <strong
                  className="font-mono text-blue-800"
                  style={{ fontFamily: "Fraunces, serif" }}
                >
                  {apresRemise.toLocaleString("fr-FR", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}{" "}
                  €
                </strong>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button asChild variant="outline">
              <Link href={`/devis/${devis.id}`}>Annuler</Link>
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving}
              className="bg-gradient-to-r from-blue-700 to-amber-600 text-white shadow hover:from-blue-800 hover:to-amber-700"
            >
              {saving ? "Enregistrement…" : "Enregistre la réduction"}
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
}

/**
 * Sprint 14 Lot 4.6 — affichage lecture seule des 5 champs brief client
 * d'un devis (Sprint 14 Lot 1). Affiché entre les lots et la réduction
 * dans EditMultiLotsPanel. L'édition complète sera scope S15+.
 */
function BriefClientReadOnly({ devis }: { devis: DevisDetail }) {
  const stockage = devis.conditions_stockage;
  const aucunChampSaisi = briefClientEstVide(devis);

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Brief client · figé
      </h2>
      <div className="rounded-lg border-l-4 border-l-blue-300 border-y border-r border-y-border border-r-border bg-white p-4 text-sm">
        {aucunChampSaisi ? (
          <p className="text-muted-foreground">
            Aucun brief client saisi pour ce devis (devis antérieur à Sprint
            14 ou contraintes non renseignées).
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Rouleau livré
              </div>
              <ul className="mt-1 space-y-1">
                <li>
                  Nb étiquettes/rouleau :{" "}
                  <strong>
                    {formatNbOrTiret(devis.nb_etiquettes_par_rouleau)}
                  </strong>
                </li>
                <li>
                  Diamètre maxi bobine :{" "}
                  <strong>
                    {formatMmOrTiret(devis.diametre_max_bobine_mm)}
                  </strong>
                </li>
                <li>
                  Nb fronts en sortie :{" "}
                  <strong>{formatNbOrTiret(devis.nb_fronts_sortie)}</strong>
                </li>
              </ul>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Entrée fichier
              </div>
              <p className="mt-1">
                <strong>{formatTypeEntree(devis.type_entree_fichier)}</strong>
              </p>
            </div>
            <div className="sm:col-span-2">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Conditions de stockage
              </div>
              {stockage ? (
                <ul className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
                  <li>
                    Humidité :{" "}
                    <strong>
                      {formatPourcentOrTiret(stockage.humidite_pct)}
                    </strong>
                  </li>
                  <li>
                    T° min :{" "}
                    <strong>{formatTemperatureOrTiret(stockage.t_min_c)}</strong>
                  </li>
                  <li>
                    T° max :{" "}
                    <strong>{formatTemperatureOrTiret(stockage.t_max_c)}</strong>
                  </li>
                  <li>
                    Lieu : <strong>{formatLieu(stockage.lieu)}</strong>
                  </li>
                </ul>
              ) : (
                <p className="mt-1 text-muted-foreground">{NON_RENSEIGNE}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
