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
import { listMatieres, type MatiereOut } from "@/lib/api";

import { useOptimisationPose } from "./OptimisationPoseStore";

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

  const handleValider = async () => {
    // PR D ou suivante : POST /api/devis avec payload multi-lots.
    // L'endpoint accepte le payload {quantite_totale, lots: [...]} depuis
    // PR B commit 5. Pour l'instant on log un toast — l'intégration finale
    // au CRUD devis est volontairement reportée car elle nécessite aussi
    // payload_input/payload_output que la persistence multi-lots structurera
    // dans une PR dédiée.
    setCreating(true);
    try {
      toast({
        title: "Devis multi-lots prêt à créer",
        description: `${selection.length} lots, Σ ${quantiteTotale.toLocaleString("fr-FR")} étiquettes. Persistance backend disponible (POST /api/devis avec lots).`,
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

      <div className="rounded-md border border-border bg-muted/30 p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div className="text-sm">
            <span className="text-muted-foreground">Total :</span>{" "}
            <strong>{quantiteTotale.toLocaleString("fr-FR")} étiquettes</strong> sur{" "}
            {selection.length} lot(s)
          </div>
          <Button onClick={handleValider} disabled={!tousLotsOntMatiere || creating}>
            {creating ? "Création…" : "Valider et créer le devis"}
          </Button>
        </div>
        {!tousLotsOntMatiere && (
          <p className="mt-2 text-xs text-amber-700">
            Renseignez une matière pour chaque lot avant validation.
          </p>
        )}
      </div>
    </section>
  );
}
