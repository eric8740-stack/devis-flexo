"use client";

import { useEffect, useState } from "react";

import { EntrepriseForm } from "@/components/EntrepriseForm";
import { getEntreprise, type Entreprise } from "@/lib/api";

export default function ParametresEntreprisePage() {
  const [entreprise, setEntreprise] = useState<Entreprise | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEntreprise()
      .then(setEntreprise)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, []);

  if (error) {
    return <p className="text-sm text-red-600">Erreur de chargement : {error}</p>;
  }
  if (!entreprise) {
    return <p className="text-sm text-muted-foreground">Chargement…</p>;
  }
  return <EntrepriseForm initial={entreprise} />;
}
