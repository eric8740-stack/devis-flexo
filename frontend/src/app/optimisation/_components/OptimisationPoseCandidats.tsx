"use client";

/**
 * Étape 2 — Tableau de tous les candidats viables + multi-sélection.
 *
 * Sprint 13 avenant. Affiche la liste TOUS les candidats triés par score
 * DESC (backend ne fait plus de top_n, cf PR B commit 3). L'utilisateur
 * peut filtrer par score (chip ≥ 30 activé par défaut) et machine,
 * cocher N lignes avec une quantité par ligne, et la somme doit égaler
 * la quantité totale saisie en étape 1.
 */
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import {
  buildIdCandidat,
  useOptimisationPose,
} from "./OptimisationPoseStore";

const SCORE_SEUIL_DEFAULT = 30;

export function OptimisationPoseCandidats() {
  const {
    candidats,
    selection,
    toggleSelection,
    setQuantiteLot,
    sommeQuantitesLots,
    quantiteTotale,
    goSaisie,
    goDetail,
  } = useOptimisationPose();

  const [scoreFiltre, setScoreFiltre] = useState(true);
  const [machineFiltre, setMachineFiltre] = useState<number | null>(null);

  const machinesDispo = useMemo(() => {
    const ids = new Set<number>();
    const labels: Record<number, string> = {};
    for (const c of candidats) {
      ids.add(c.machine_id);
      labels[c.machine_id] = c.noms_machines_compatibles[0] ?? `Machine #${c.machine_id}`;
    }
    return Array.from(ids).map((id) => ({ id, label: labels[id] }));
  }, [candidats]);

  const candidatsAffiches = useMemo(() => {
    return candidats.filter((c) => {
      if (scoreFiltre && c.score < SCORE_SEUIL_DEFAULT) return false;
      if (machineFiltre !== null && c.machine_id !== machineFiltre) return false;
      return true;
    });
  }, [candidats, scoreFiltre, machineFiltre]);

  const sommeOK = sommeQuantitesLots === quantiteTotale && selection.length > 0;
  const ecart = sommeQuantitesLots - quantiteTotale;

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Étape 2 — Candidats viables</h2>
          <p className="text-sm text-muted-foreground">
            Qté totale {quantiteTotale.toLocaleString("fr-FR")} · {candidats.length} configurations
            viables (triées par score DESC)
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={goSaisie}>
          ← Modifier la saisie
        </Button>
      </header>

      {/* Filtres */}
      <div className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-muted/30 p-3 text-sm">
        <label className="flex cursor-pointer items-center gap-1">
          <input
            type="checkbox"
            checked={scoreFiltre}
            onChange={(e) => setScoreFiltre(e.target.checked)}
            className="h-4 w-4 accent-foreground"
          />
          <span>Score ≥ {SCORE_SEUIL_DEFAULT}</span>
        </label>
        <label className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Machine</span>
          <select
            className="rounded border border-input bg-background px-2 py-1 text-sm"
            value={machineFiltre ?? ""}
            onChange={(e) =>
              setMachineFiltre(e.target.value ? Number(e.target.value) : null)
            }
          >
            <option value="">Toutes</option>
            {machinesDispo.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <span className="ml-auto text-xs text-muted-foreground">
          {candidatsAffiches.length} affichées
        </span>
      </div>

      {/* Tableau candidats */}
      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr className="text-left">
              <th className="px-2 py-2"></th>
              <th className="px-2 py-2">Cylindre</th>
              <th className="px-2 py-2">Machine</th>
              <th className="px-2 py-2">Poses</th>
              <th className="px-2 py-2">Δ dev</th>
              <th className="px-2 py-2">Δ laize</th>
              <th className="px-2 py-2">Score</th>
              <th className="px-2 py-2">Sens</th>
              <th className="px-2 py-2">Quantité du lot</th>
            </tr>
          </thead>
          <tbody>
            {candidatsAffiches.map((c) => {
              const id = buildIdCandidat(c);
              const lot = selection.find((s) => s.id_candidat === id);
              const coche = lot !== undefined;
              return (
                <tr
                  key={id}
                  className={
                    "border-t border-border " +
                    (coche ? "bg-blue-50/50" : "hover:bg-muted/30")
                  }
                >
                  <td className="px-2 py-2">
                    <input
                      type="checkbox"
                      checked={coche}
                      onChange={() => toggleSelection(c)}
                      className="h-4 w-4 accent-foreground"
                    />
                  </td>
                  <td className="px-2 py-2 font-medium">
                    {c.z_cylindre_mm} mm
                    <span className="ml-1 text-xs text-muted-foreground">
                      ({c.nb_dents_cylindre} dents)
                    </span>
                  </td>
                  <td className="px-2 py-2">
                    {c.noms_machines_compatibles[0] ?? `#${c.machine_id}`}
                  </td>
                  <td className="px-2 py-2 font-mono text-xs">
                    {c.nb_poses_laize}×{c.nb_poses_dev}={c.nb_poses_total}
                  </td>
                  <td className="px-2 py-2 font-mono text-xs">
                    {c.intervalle_dev_reel_mm} mm
                  </td>
                  <td className="px-2 py-2 font-mono text-xs">
                    {c.intervalle_laize_reel_mm} mm
                  </td>
                  <td className="px-2 py-2 font-mono">
                    {c.score.toFixed(0)}
                  </td>
                  <td className="px-2 py-2 text-xs">
                    {c.sens_enroulement_libelle}
                  </td>
                  <td className="px-2 py-2">
                    {coche && (
                      <Input
                        type="number"
                        min={1}
                        value={lot.quantite || ""}
                        onChange={(e) =>
                          setQuantiteLot(id, parseInt(e.target.value || "0", 10))
                        }
                        placeholder="qté"
                        className="w-28 text-right"
                      />
                    )}
                  </td>
                </tr>
              );
            })}
            {candidatsAffiches.length === 0 && (
              <tr>
                <td colSpan={9} className="px-2 py-4 text-center text-sm text-muted-foreground">
                  Aucune configuration ne correspond aux filtres.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Récap + bouton continuer */}
      <div className="flex flex-wrap items-baseline justify-between gap-3 rounded-md border border-border bg-muted/30 p-3 text-sm">
        <div>
          <span className="text-muted-foreground">Σ sélectionné : </span>
          <strong>{sommeQuantitesLots.toLocaleString("fr-FR")}</strong>
          <span className="text-muted-foreground"> / {quantiteTotale.toLocaleString("fr-FR")}</span>
          {sommeOK && <span className="ml-2 font-semibold text-emerald-700">✅</span>}
          {!sommeOK && ecart !== 0 && selection.length > 0 && (
            <span className="ml-2 text-amber-700">
              ({ecart > 0 ? "+" : ""}{ecart})
            </span>
          )}
        </div>
        <Button onClick={goDetail} disabled={!sommeOK}>
          Continuer avec ces {selection.length} lots →
        </Button>
      </div>
    </section>
  );
}
