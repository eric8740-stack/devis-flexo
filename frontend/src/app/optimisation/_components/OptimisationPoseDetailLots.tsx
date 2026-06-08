"use client";

/**
 * Étape 3 — Détail des lots sélectionnés + édition matière par lot + visuel BAT.
 *
 * Sprint 13 avenant + Brief #28. Affiche une card par lot sélectionné en
 * étape 2, avec un sélecteur matière obligatoire et le visuel BAT généré
 * par le composant `SchemaImplantation` (Vue A + Vue B + Vue C) :
 *
 *   ⚠️ SACRED — le composant `SchemaImplantation` est réutilisé 1:1, sans
 *   modification de son rendu (SVG, layout, positions des A, rotations,
 *   vignettes, légendes). Brief #28 §11. Les data du candidat sélectionné
 *   sont passées en props au composant tel quel.
 *
 * Multi-lots métier : chaque lot a SA matière, indépendante des autres
 * lots du devis (LOT 1 peut être PP couché 80g, LOT 2 PET blanc 50µ).
 * Pas de matière "globale" au niveau devis. Validation : le bouton
 * "Valider et créer le devis" est désactivé tant qu'un lot n'a pas de
 * matière sélectionnée (FK NOT NULL sur lot_production.matiere_id).
 */
import { useEffect, useState } from "react";

import { SchemaImplantation } from "@/components/SchemaImplantation";
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
  listMatieres,
  type MatiereOut,
} from "@/lib/api";

import { useOptimisationPose } from "./OptimisationPoseStore";

export function OptimisationPoseDetailLots() {
  const {
    selection,
    setMatiereLot,
    setEpaisseurSaisieLot,
    quantiteTotale,
    laizeEtiqMm,
    devEtiqMm,
    mandrinMm,
    goCandidats,
    goSaisie,
    goRebobinage,
  } = useOptimisationPose();
  const { toast } = useToast();

  const [matieres, setMatieres] = useState<MatiereOut[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    listMatieres()
      .then((m) => {
        if (!cancelled) setMatieres(m);
      })
      .catch((err) => {
        toast({
          title: "Chargement matières impossible",
          description: err instanceof Error ? err.message : "Erreur inconnue",
          variant: "destructive",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [toast]);

  const tousLotsOntMatiere = selection.every((s) => s.matiere_id !== null);
  const sommeQuantites = selection.reduce((acc, s) => acc + s.quantite, 0);
  const sommeOK = sommeQuantites === quantiteTotale && selection.length > 0;
  // Sprint 16 Lot D — l'étape 3 bascule désormais vers "rebobinage" puis
  // "chiffrage". Avant Sprint 16 : étape 3 → chiffrage direct (Brief #33).
  const peutPasserSuivant = tousLotsOntMatiere && sommeOK;

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Étape 3 — Détail des lots</h2>
          <p className="text-sm text-muted-foreground">
            {selection.length} lots · Σ {quantiteTotale.toLocaleString("fr-FR")} étiquettes
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => goCandidats(
            [],  // candidats déjà en store, pas besoin de re-fournir
            quantiteTotale,
            laizeEtiqMm,
            devEtiqMm,
            mandrinMm,
          )}>
            ← Retour candidats
          </Button>
          <Button variant="ghost" size="sm" onClick={goSaisie}>
            Modifier la saisie
          </Button>
        </div>
      </header>

      <div className="grid gap-4">
        {selection.map((lot, idx) => {
          const matiereLot =
            (matieres ?? []).find((m) => m.id === lot.matiere_id) ?? null;
          // Bug #6 (6.2) — l'épaisseur pilote le Ø bobine à l'étape suivante.
          // Matière avec épaisseur catalogue → lecture seule. Matière sans
          // épaisseur (caractérisée au grammage) → saisie opérateur requise,
          // sinon le backend retombe sur 150 µm (ultime fallback).
          const epaisseurCatalogue = matiereLot?.epaisseur_microns ?? null;
          const matiereSansEpaisseur =
            matiereLot !== null && epaisseurCatalogue === null;
          return (
          <Card key={lot.id_candidat}>
            <CardHeader>
              <CardTitle className="text-lg">
                Lot {idx + 1} — {lot.candidat.nb_poses_laize}×{lot.candidat.nb_poses_dev}={" "}
                {lot.candidat.nb_poses_total} poses
              </CardTitle>
              <CardDescription>
                Cyl {lot.candidat.nb_dents_cylindre} dents ({lot.candidat.z_cylindre_mm} mm) ·{" "}
                {lot.candidat.noms_machines_compatibles[0] ?? `Machine #${lot.candidat.machine_id}`}{" "}
                · {lot.quantite.toLocaleString("fr-FR")} étiquettes · score{" "}
                {lot.candidat.score.toFixed(0)}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Matière * (obligatoire)
                </label>
                <select
                  className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={lot.matiere_id ?? ""}
                  onChange={(e) =>
                    setMatiereLot(lot.id_candidat, Number(e.target.value))
                  }
                >
                  <option value="">— Sélectionner une matière —</option>
                  {(matieres ?? []).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.libelle}
                      {m.epaisseur_microns ? ` (${m.epaisseur_microns} µm)` : ""}
                    </option>
                  ))}
                </select>
              </div>

              {/* Bug #6 (6.2) — épaisseur matière du lot, pilote le Ø bobine. */}
              {matiereLot !== null && !matiereSansEpaisseur && (
                <p
                  className="text-xs text-muted-foreground"
                  data-testid={`epaisseur-catalogue-${idx}`}
                >
                  Épaisseur catalogue : <strong>{epaisseurCatalogue} µm</strong>{" "}
                  (utilisée pour le calcul du Ø bobine).
                </p>
              )}
              {matiereSansEpaisseur && (
                <div className="space-y-2 rounded-md border border-amber-300 bg-amber-50 p-3">
                  <label
                    htmlFor={`epaisseur-saisie-${idx}`}
                    className="text-xs font-semibold uppercase tracking-wide text-amber-900"
                  >
                    Épaisseur matière (µm) — saisie requise
                  </label>
                  <input
                    id={`epaisseur-saisie-${idx}`}
                    data-testid={`epaisseur-saisie-${idx}`}
                    type="number"
                    min={1}
                    step={1}
                    inputMode="numeric"
                    className="block w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={lot.epaisseur_saisie_um ?? ""}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === "") {
                        setEpaisseurSaisieLot(lot.id_candidat, null);
                        return;
                      }
                      const n = parseInt(v, 10);
                      setEpaisseurSaisieLot(
                        lot.id_candidat,
                        Number.isFinite(n) && n > 0 ? n : null,
                      );
                    }}
                    placeholder="ex: 90"
                  />
                  <p className="text-xs text-amber-800">
                    Cette matière n&apos;a pas d&apos;épaisseur au catalogue.
                    Renseigne-la pour un Ø bobine juste — sinon le calcul
                    retombe sur 150 µm par défaut.
                  </p>
                </div>
              )}

              {/* L1 — décompo laize (lecture seule) depuis le contrat
                  partagé `geometrie_laize`. Informatif : aucun impact prix.
                  Absent pour les devis legacy (payload_visuel pré-L1) → masqué. */}
              {lot.candidat.geometrie_laize && (
                <div
                  data-testid={`decompo-laize-${idx}`}
                  className="rounded-md border border-border bg-muted/20 p-3 text-sm"
                >
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Décompo laize papier
                  </span>
                  <div className="mt-1 font-mono">
                    Imprimé{" "}
                    <strong>
                      {lot.candidat.geometrie_laize.laize_plaque_mm} mm
                    </strong>{" "}
                    + 2 × bord{" "}
                    <strong>
                      {lot.candidat.geometrie_laize.bord_lateral_mm} mm
                    </strong>{" "}
                    ={" "}
                    <strong>
                      {lot.candidat.geometrie_laize.laize_papier_mm} mm
                    </strong>{" "}
                    de laize papier réelle
                  </div>
                  {lot.candidat.forcage_bord_lateral && (
                    <div
                      data-testid={`bord-force-${idx}`}
                      className="mt-1 text-xs text-amber-800"
                    >
                      ⚠ Bord latéral forcé
                      {lot.candidat.motif_bord_lateral
                        ? ` — ${lot.candidat.motif_bord_lateral}`
                        : " (motif manquant)"}
                    </div>
                  )}
                  {/* Lot back A — mode sans outil : déchet latéral (stock −
                      utile) + nb bobines filles, exposés par geometrie_laize. */}
                  {lot.candidat.geometrie_laize.dechet_lateral_mm != null && (
                    <div
                      data-testid={`dechet-lateral-${idx}`}
                      className="mt-1 font-mono text-xs"
                    >
                      Déchet latéral : stock{" "}
                      <strong>
                        {lot.candidat.geometrie_laize.laize_stock_mm} mm
                      </strong>{" "}
                      − utile{" "}
                      <strong>
                        {lot.candidat.geometrie_laize.laize_utile_mm} mm
                      </strong>{" "}
                      ={" "}
                      <strong>
                        {lot.candidat.geometrie_laize.dechet_lateral_mm} mm
                      </strong>
                      {lot.candidat.geometrie_laize.nb_filles != null && (
                        <>
                          {" "}
                          · <strong>
                            {lot.candidat.geometrie_laize.nb_filles}
                          </strong>{" "}
                          bobine(s) fille(s)
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}

              <SchemaImplantation
                config={lot.candidat}
                laizeEtiqMm={laizeEtiqMm}
                devEtiqMm={devEtiqMm}
                mandrinMm={mandrinMm}
              />
            </CardContent>
          </Card>
          );
        })}
      </div>

      {/* Sprint 16 Lot D — étape 3 → rebobinage → chiffrage. L'étape
          rebobinage (paramètres bobine client + arbitrage pré-coupé /
          découpe interne) est intercalée avant le chiffrage final. */}
      <div className="rounded-lg border-2 border-blue-200 bg-gradient-to-br from-blue-50/50 to-amber-50/30 p-6">
        <div className="space-y-1 text-center">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            Récap devis
          </p>
          <p className="text-lg font-semibold">
            {selection.length} lot(s) · {quantiteTotale.toLocaleString("fr-FR")}{" "}
            étiquettes au total
          </p>
        </div>

        <div className="mt-5 flex justify-center">
          <Button
            size="lg"
            onClick={goRebobinage}
            disabled={!peutPasserSuivant}
            className="bg-gradient-to-r from-blue-700 to-amber-600 px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:from-blue-800 hover:to-amber-700 hover:shadow-lg disabled:from-gray-300 disabled:to-gray-400 disabled:shadow-none"
          >
            Étape suivante : rebobinage →
          </Button>
        </div>

        {!tousLotsOntMatiere && (
          <p className="mt-3 text-center text-sm text-amber-700">
            ℹ Renseigne une matière pour chaque lot avant de passer au rebobinage.
          </p>
        )}
        {tousLotsOntMatiere && !sommeOK && (
          <p className="mt-3 text-center text-sm text-amber-700">
            ℹ Σ quantités lots ({sommeQuantites.toLocaleString("fr-FR")}) ≠
            quantité totale ({quantiteTotale.toLocaleString("fr-FR")}). Retour
            étape 2 pour ajuster.
          </p>
        )}
      </div>
    </section>
  );
}
