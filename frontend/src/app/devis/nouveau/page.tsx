"use client";

import { useState } from "react";

import { DevisCalculForm } from "@/components/DevisCalculForm";
import { DevisResult } from "@/components/DevisResult";
import type { DevisCalculResult } from "@/lib/api";

export default function NouveauDevisPage() {
  const [result, setResult] = useState<DevisCalculResult | null>(null);

  return (
    <main className="container mx-auto max-w-5xl p-4 sm:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Calculer un devis</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Moteur de coût v2 — 7 postes calculés à partir des seeds
          (tarifs, complexes, machines). Le formulaire est pré-rempli sur le
          cas-test médian validé : un clic sur « Calculer le devis » doit
          retourner exactement <strong>1 449,09 €</strong> HT.
        </p>
      </header>

      <DevisCalculForm onResult={setResult} />

      {result && (
        <section className="mt-8">
          <DevisResult data={result} />
        </section>
      )}
    </main>
  );
}
