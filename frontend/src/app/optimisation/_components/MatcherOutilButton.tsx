"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { ApiError, listMachines, type Machine } from "@/lib/api";
import {
  postMatcherOutil,
  type MatcherOutilMatch,
} from "@/lib/api/matcherOutil";

import { useOptimisationPose } from "./OptimisationPoseStore";

// Sprint 14 Lot 4.5 — UI matcher-outil.
// Localisation : étape « saisie » du workflow optim, juste avant le bouton
// « Trouver configurations ». Cherche un cylindre du parc compatible avec
// l'étiquette saisie + brief client (nb fronts sortie), sur UNE machine
// sélectionnée. Si aucun match → backend renvoie 1 entrée avec
// `cylindre_id=null` (cas « nouvel outil sur mesure ~200 €»).
//
// Heuristique sélecteur machine :
//   0 machine active  → bouton bloqué + message admin
//   1 machine active  → auto-sélectionnée + info texte
//   N machines        → <select> dropdown + bouton

interface Props {
  laizeEtiqMm: number;
  devEtiqMm: number;
  intervalleDevMm: number;
  intervalleLaizeMm: number;
}

function formatEuros(s: string): string {
  const n = parseFloat(s);
  if (Number.isNaN(n)) return s;
  return (
    n.toLocaleString("fr-FR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) + " €"
  );
}

function formatMm(s: string): string {
  const n = parseFloat(s);
  if (Number.isNaN(n)) return s;
  return n.toFixed(1) + " mm";
}

export function MatcherOutilButton({
  laizeEtiqMm,
  devEtiqMm,
  intervalleDevMm,
  intervalleLaizeMm,
}: Props) {
  const { briefClient, outilSelectionne, setOutilSelectionne } =
    useOptimisationPose();

  const [machines, setMachines] = useState<Machine[] | null>(null);
  const [machineId, setMachineId] = useState<number | null>(null);
  const [matches, setMatches] = useState<MatcherOutilMatch[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listMachines()
      .then((ms) => {
        if (cancelled) return;
        const actives = ms.filter((m) => m.actif);
        setMachines(actives);
        if (actives.length >= 1) setMachineId(actives[0]!.id);
      })
      .catch(() => {
        if (!cancelled) setMachines([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const inputsValides = laizeEtiqMm > 0 && devEtiqMm > 0;

  const handleCherchOutils = async () => {
    if (machineId === null) return;
    setLoading(true);
    setError(null);
    setMatches(null);
    try {
      const res = await postMatcherOutil({
        machine_id: machineId,
        laize_etiquette_mm: laizeEtiqMm,
        dev_etiquette_mm: devEtiqMm,
        intervalle_dev_mm: intervalleDevMm,
        intervalle_laize_mm: intervalleLaizeMm,
        nb_fronts_min: briefClient.nb_fronts_sortie ?? 1,
      });
      setMatches(res.matches);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setError("Étiquette trop grande ou aucun match faisable.");
      } else {
        setError(err instanceof Error ? err.message : "Erreur inconnue");
      }
    } finally {
      setLoading(false);
    }
  };

  if (machines === null) {
    return (
      <p className="text-sm text-muted-foreground">
        Chargement du parc machines…
      </p>
    );
  }

  if (machines.length === 0) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-amber-800">
            Configurez une machine dans Admin avant d&apos;utiliser le matcher
            d&apos;outils.
          </p>
        </CardContent>
      </Card>
    );
  }

  const machineSelectionnee = machines.find((m) => m.id === machineId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Outils compatibles</CardTitle>
        <CardDescription>
          Vérifie si un cylindre magnétique de ton parc convient déjà au format
          saisi avant de lancer l&apos;optimisation complète.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {machines.length === 1 ? (
          <p className="text-sm text-muted-foreground">
            Outils compatibles pour <strong>{machineSelectionnee?.nom}</strong>
          </p>
        ) : (
          <div className="space-y-2">
            <Label htmlFor="matcher-machine">Machine</Label>
            <select
              id="matcher-machine"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring sm:max-w-md"
              value={machineId ?? ""}
              onChange={(e) => {
                setMachineId(Number(e.target.value));
                setMatches(null);
                setError(null);
              }}
            >
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nom}
                </option>
              ))}
            </select>
          </div>
        )}

        <Button
          type="button"
          onClick={handleCherchOutils}
          disabled={loading || !inputsValides || machineId === null}
        >
          {loading ? "Recherche…" : "Voir outils compatibles"}
        </Button>

        {!inputsValides && (
          <p className="text-xs text-muted-foreground">
            Renseigne d&apos;abord la laize et le développé de l&apos;étiquette.
          </p>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        {matches && matches.length > 0 && (
          <div className="space-y-3" data-testid="matcher-results">
            {matches.map((m, idx) => {
              const estNouvelOutil = m.cylindre_id === null;
              const isSelected =
                outilSelectionne !== null &&
                outilSelectionne.cylindre_id === m.cylindre_id &&
                outilSelectionne.nb_dents === m.nb_dents;
              return (
                <button
                  type="button"
                  key={`${m.cylindre_id ?? "new"}-${m.nb_dents}-${idx}`}
                  onClick={() => setOutilSelectionne(m)}
                  className={`w-full rounded-md border p-3 text-left transition-colors ${
                    isSelected
                      ? "border-foreground bg-accent"
                      : estNouvelOutil
                        ? "border-amber-300 bg-amber-50 hover:bg-amber-100"
                        : "border-border bg-background hover:bg-accent/40"
                  }`}
                  data-testid={`match-${idx}`}
                >
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-sm font-medium">
                      {estNouvelOutil ? (
                        <span>
                          🛠️ Nouvel outil à fabriquer (~
                          {formatEuros(m.cout_outil_eur)})
                        </span>
                      ) : (
                        <span>
                          Cylindre #{m.cylindre_id} — {m.nb_dents} dents · ø{" "}
                          {formatMm(m.developpe_mm)}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Score : {m.score_efficacite.toFixed(2)}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {m.nb_poses_dev}×{m.nb_poses_laize} = {m.nb_poses_total}{" "}
                    pose(s) par tour
                    {!estNouvelOutil &&
                      ` · ${formatEuros(m.cout_outil_eur)} HT`}
                  </div>
                  {isSelected && (
                    <div className="mt-2 text-xs font-semibold text-foreground">
                      ✓ Sélectionné
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
