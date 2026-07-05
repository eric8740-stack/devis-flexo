"use client";

import { useEffect, useState } from "react";

import { EntrepriseForm } from "@/components/EntrepriseForm";
import { getEntreprise, type Entreprise } from "@/lib/api";

export default function ParametresEntreprisePage() {
  const [entreprise, setEntreprise] = useState<Entreprise | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Flag `cancelled` (audit 05/07/2026 M5) : ignore une réponse arrivée
  // après le démontage du composant.
  useEffect(() => {
    let cancelled = false;
    getEntreprise()
      .then((res) => {
        if (!cancelled) setEntreprise(res);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="text-sm text-red-600">Erreur de chargement : {error}</p>;
  }
  if (!entreprise) {
    return <p className="text-sm text-muted-foreground">Chargement…</p>;
  }
  return <EntrepriseForm initial={entreprise} />;
}
