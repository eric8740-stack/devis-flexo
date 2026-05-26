"use client";

/**
 * Sprint 16 — Hook partagé de la liste clients du tenant.
 *
 * Plusieurs composants du workflow optimisation ont besoin de la même
 * liste (sélecteur en tête de l'étape rebobinage + sélecteur en bas de
 * l'étape chiffrage). On évite un double fetch via un cache module-scoped
 * stocké sous forme de `Promise<Client[]>` partagée. Le premier
 * consommateur déclenche le fetch ; les suivants attendent la même
 * promesse résolue.
 *
 * Le cache est volontairement non invalidé : un client ajouté/modifié en
 * cours de session du workflow (cas rare) ne sera pas reflété ; recharger
 * la page suffit à rafraîchir. Pas de gestion fine d'invalidation pour
 * rester KISS.
 */
import { useEffect, useState } from "react";

import { listClients, type Client } from "@/lib/api";

let cache: Promise<Client[]> | null = null;

function chargerClientsCache(): Promise<Client[]> {
  if (cache === null) {
    cache = listClients().catch((err) => {
      // Reset le cache pour qu'un re-mount après erreur réessaie.
      cache = null;
      throw err;
    });
  }
  return cache;
}

interface UseClientsResult {
  clients: Client[];
  loading: boolean;
  error: string | null;
}

export function useClientsListe(): UseClientsResult {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    chargerClientsCache()
      .then((rows) => {
        if (cancelled) return;
        setClients(rows);
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

  return { clients, loading, error };
}

/**
 * Utilitaire de test : reset du cache module pour isoler les tests
 * Vitest. À n'utiliser que depuis les tests.
 */
export function _resetClientsListeCacheForTests(): void {
  cache = null;
}
