"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ComplexeForm } from "@/components/ComplexeForm";
import { useToast } from "@/hooks/use-toast";
import {
  getComplexe,
  updateComplexe,
  type Complexe,
  type ComplexeCreate,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditComplexePage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [item, setItem] = useState<Complexe | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getComplexe(id)
      .then(setItem)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: ComplexeCreate) => {
    try {
      const updated = await updateComplexe(id, data);
      toast({
        title: "Complexe mis à jour",
        description: `« ${updated.reference} »`,
      });
      router.push("/complexes");
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  return (
    <main className="container mx-auto max-w-3xl p-8">
      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !item ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <ComplexeForm
          title={`Complexe #${item.id} — ${item.reference}`}
          submitLabel="Enregistrer"
          initial={extractCreate(item)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/complexes")}
        />
      )}
    </main>
  );
}

function extractCreate(c: Complexe): ComplexeCreate {
  const { id: _id, date_creation: _dc, date_maj: _dm, ...rest } = c;
  void _id;
  void _dc;
  void _dm;
  return {
    ...rest,
    prix_m2_eur: Number(rest.prix_m2_eur),
  };
}
