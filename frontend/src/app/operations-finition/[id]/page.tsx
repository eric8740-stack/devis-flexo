"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { OperationFinitionForm } from "@/components/OperationFinitionForm";
import { useToast } from "@/hooks/use-toast";
import {
  getOperationFinition,
  updateOperationFinition,
  type OperationFinition,
  type OperationFinitionCreate,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditOperationPage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [item, setItem] = useState<OperationFinition | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOperationFinition(id)
      .then(setItem)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: OperationFinitionCreate) => {
    try {
      const updated = await updateOperationFinition(id, data);
      toast({
        title: "Opération mise à jour",
        description: `« ${updated.nom} »`,
      });
      router.push("/operations-finition");
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
        <OperationFinitionForm
          title={`Opération #${item.id}`}
          submitLabel="Enregistrer"
          initial={extractCreate(item)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/operations-finition")}
        />
      )}
    </main>
  );
}

function extractCreate(o: OperationFinition): OperationFinitionCreate {
  const { id: _id, date_creation: _dc, date_maj: _dm, ...rest } = o;
  void _id;
  void _dc;
  void _dm;
  return rest;
}
