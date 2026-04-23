"use client";

import { useEffect, useState } from "react";

import { EntrepriseForm } from "@/components/EntrepriseForm";
import { getEntreprise, type Entreprise } from "@/lib/api";

export default function ParametresPage() {
  const [entreprise, setEntreprise] = useState<Entreprise | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEntreprise()
      .then(setEntreprise)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, []);

  return (
    <main className="container mx-auto max-w-3xl p-8">
      {error ? (
        <p className="text-sm text-red-600">Erreur de chargement : {error}</p>
      ) : !entreprise ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <EntrepriseForm initial={entreprise} />
      )}
    </main>
  );
}
