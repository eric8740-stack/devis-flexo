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
import { useRouter } from "next/navigation";
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
  createDevis,
  listMatieres,
  type DevisCreate,
  type LotProductionCreatePayload,
  type MatiereOut,
} from "@/lib/api";

import { useOptimisationPose } from "./OptimisationPoseStore";

function _sensEnroulementToInt(se: string): number {
  // "SE1" → 1, "SE8" → 8 (convention métier flexo, single source of truth
  // backend dans `app/services/rotation_se.py`).
  return parseInt(se.replace("SE", ""), 10);
}

export function OptimisationPoseDetailLots() {
  const {
    selection,
    setMatiereLot,
    quantiteTotale,
    laizeEtiqMm,
    devEtiqMm,
    mandrinMm,
    goCandidats,
    goSaisie,
  } = useOptimisationPose();
  const { toast } = useToast();
  const router = useRouter();

  const [matieres, setMatieres] = useState<MatiereOut[] | null>(null);
  const [creating, setCreating] = useState(false);

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
  const peutCreer = tousLotsOntMatiere && sommeOK && !creating;

  const handleValider = async () => {
    if (!peutCreer) return;
    setCreating(true);
    try {
      // Construction du payload conforme à DevisCreate (PR B #26 commit 5) :
      // - `lots` + `quantite_totale` activent le mode multi-lots (création de N
      //   LotProduction en cascade côté backend).
      // - `payload_input`/`payload_output` sont des dicts JSON libres servant
      //   au moteur cost_engine (calcul du HT à venir séparément). On y stocke
      //   les paramètres de saisie (étape 1) + un placeholder ht=0 — le coût
      //   réel sera recalculé via /api/cost/calculer après création.
      const premierLot = selection[0]!.candidat;
      const lotsPayload: LotProductionCreatePayload[] = selection.map((s) => ({
        cylindre_id: s.candidat.cylindre_id,
        machine_id: s.candidat.machine_id,
        nb_poses_dev: s.candidat.nb_poses_dev,
        nb_poses_laize: s.candidat.nb_poses_laize,
        sens_enroulement: _sensEnroulementToInt(s.candidat.sens_enroulement),
        quantite: s.quantite,
        matiere_id: s.matiere_id as number,
        intervalle_dev_reel_mm: String(s.candidat.intervalle_dev_reel_mm),
        intervalle_laize_reel_mm: String(s.candidat.intervalle_laize_reel_mm),
        largeur_plaque_mm: String(s.candidat.largeur_plaque_mm),
        score_optim: s.candidat.score,
      }));
      const payload: DevisCreate = {
        payload_input: {
          machine_id: premierLot.machine_id,
          format_etiquette_largeur_mm: laizeEtiqMm,
          format_etiquette_hauteur_mm: devEtiqMm,
          mode_calcul: "manuel",
          source: "optim_multi_lots",
          nb_lots: selection.length,
          mandrin_mm: mandrinMm,
        },
        payload_output: {
          mode: "manuel",
          prix_vente_ht_eur: "0.00",
          note: "Coût lots à calculer post-création via /api/cost/calculer.",
        },
        statut: "brouillon",
        quantite_totale: quantiteTotale,
        lots: lotsPayload,
      };
      const devis = await createDevis(payload);
      toast({
        title: "Devis créé ✓",
        description: `Devis ${devis.numero} créé avec ${selection.length} lot(s). Tu le retrouves dans la liste.`,
      });
      // Patch #31 — redirect vers la liste des devis (et non /devis/{id}).
      // Le détail d'un devis multi-lots nécessite un rendu spécifique qui
      // n'existe pas encore : la page /devis/{id} utilise `DevisResult` qui
      // attend `payload_output.postes` (mode mono cost_engine standard).
      // Notre payload_output multi-lots est minimal (pas de postes calculés)
      // → DevisResult plantait au render avec "client-side exception".
      // Redirect liste = chemin user safe ; le rendu détail multi-lots fait
      // l'objet d'un brief dédié (hors scope patch #31).
      router.push("/devis");
    } catch (err) {
      toast({
        title: "Création du devis impossible",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setCreating(false);
    }
  };

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
        {selection.map((lot, idx) => (
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

              <SchemaImplantation
                config={lot.candidat}
                laizeEtiqMm={laizeEtiqMm}
                devEtiqMm={devEtiqMm}
                mandrinMm={mandrinMm}
              />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Récap + CTA primary prominent (Brief #30 commit 1).
          Bouton centré sous le récap, gradient bleu→ambre, taille lg,
          loading state avec spinner inline, redirect vers /devis/{id}
          après succès POST /api/devis. */}
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
            onClick={handleValider}
            disabled={!peutCreer}
            className="bg-gradient-to-r from-blue-700 to-amber-600 px-8 py-6 text-base font-semibold text-white shadow-md transition-all hover:from-blue-800 hover:to-amber-700 hover:shadow-lg disabled:from-gray-300 disabled:to-gray-400 disabled:shadow-none"
          >
            {creating ? (
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
                Création en cours…
              </span>
            ) : (
              <>✓ Valider et créer le devis</>
            )}
          </Button>
        </div>

        {!tousLotsOntMatiere && (
          <p className="mt-3 text-center text-sm text-amber-700">
            ℹ Renseigne une matière pour chaque lot avant validation.
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
