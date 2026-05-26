"use client";

/**
 * Sprint 16 — Hook de chargement des rebobineuses du tenant courant.
 *
 * Câblé sur `GET /api/machines-rebobineuses` (router rebobinage,
 * PR #43 backend). Scope strict tenant côté backend — un tenant ne
 * voit JAMAIS les rebobineuses d'un autre. Tri backend par nom ASC
 * puis id ASC : on respecte cet ordre côté UI sans re-tri local.
 *
 * Le hook expose une signature minimaliste consommée par
 * `OptimisationRebobinage` : `{ machines, loading, error }`. Les
 * tests RTL mockent ce hook via `vi.mock` pour injecter les 3 cas
 * (1 / N / 0 machines) sans dépendre du réseau réel.
 */
import { useEffect, useState } from "react";

import {
  listMachinesRebobineuses,
  type MachineRebobineuseListItem,
} from "@/lib/api";

// Type ré-exporté pour les consommateurs UI + tests — historique du
// pré-câblage (option 3) où le contrat n'était pas encore figé.
// Aujourd'hui aligné sur `MachineRebobineuseListItem` côté backend.
export type MachineRebobineuseLite = MachineRebobineuseListItem;

interface UseRebobineusesResult {
  machines: MachineRebobineuseLite[];
  loading: boolean;
  error: string | null;
}

export function useRebobineusesDuTenant(): UseRebobineusesResult {
  const [machines, setMachines] = useState<MachineRebobineuseLite[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listMachinesRebobineuses()
      .then((rows) => {
        if (cancelled) return;
        setMachines(rows);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Erreur inconnue");
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { machines, loading, error };
}
