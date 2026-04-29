"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DevisCalculForm } from "@/components/DevisCalculForm";
import { DevisResult } from "@/components/DevisResult";
import { DevisSaveBar } from "@/components/DevisSaveBar";
import { Button } from "@/components/ui/button";
import {
  getDevisDetail,
  type DevisCalculResult,
  type DevisDetail,
  type DevisInput,
} from "@/lib/api";

export default function EditDevisPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);

  const [devis, setDevis] = useState<DevisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DevisCalculResult | null>(null);
  const [input, setInput] = useState<DevisInput | null>(null);

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError("ID de devis invalide");
      return;
    }
    getDevisDetail(id)
      .then(setDevis)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  if (error) {
    return (
      <main className="container mx-auto max-w-5xl p-4 sm:p-8">
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive"
        >
          <strong>Erreur :</strong> {error}
        </div>
        <div className="mt-4">
          <Button asChild variant="outline">
            <Link href="/devis">↩ Retour à la liste</Link>
          </Button>
        </div>
      </main>
    );
  }

  if (!devis) {
    return (
      <main className="container mx-auto max-w-5xl p-4 sm:p-8">
        <div className="text-sm text-muted-foreground">Chargement…</div>
      </main>
    );
  }

  const initialPayloadInput = devis.payload_input as unknown as DevisInput;

  return (
    <main className="container mx-auto max-w-5xl p-4 sm:p-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold font-mono">
            Modifier {devis.numero}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Recalculez puis sauvegardez pour mettre à jour ce devis.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/devis/${devis.id}`}>↩ Annuler</Link>
        </Button>
      </header>

      <DevisCalculForm
        initialPayloadInput={initialPayloadInput}
        onResult={(r, i) => {
          setResult(r);
          setInput(i ?? null);
        }}
      />

      {result && (
        <section className="mt-8 grid gap-6">
          <DevisResult data={result} />
          {input && (
            <DevisSaveBar
              input={input}
              result={result}
              mode="edit"
              devisId={devis.id}
              initialClientId={devis.client_id}
              initialStatut={devis.statut}
              initialCylindreZ={devis.cylindre_choisi_z}
              initialCylindreNbEtiq={devis.cylindre_choisi_nb_etiq}
              onSaved={(savedId) => router.push(`/devis/${savedId}`)}
            />
          )}
        </section>
      )}
    </main>
  );
}
