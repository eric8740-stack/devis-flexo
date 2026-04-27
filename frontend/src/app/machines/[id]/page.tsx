"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MachineForm } from "@/components/MachineForm";
import { useToast } from "@/hooks/use-toast";
import {
  getMachine,
  updateMachine,
  type Machine,
  type MachineCreate,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditMachinePage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [item, setItem] = useState<Machine | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMachine(id)
      .then(setItem)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: MachineCreate) => {
    try {
      const updated = await updateMachine(id, data);
      toast({ title: "Machine mise à jour", description: `« ${updated.nom} »` });
      router.push("/machines");
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
        <MachineForm
          title={`Machine #${item.id}`}
          submitLabel="Enregistrer"
          initial={extractCreate(item)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/machines")}
        />
      )}
    </main>
  );
}

function extractCreate(m: Machine): MachineCreate {
  const { id: _id, date_creation: _dc, date_maj: _dm, ...rest } = m;
  void _id;
  void _dc;
  void _dm;
  return rest;
}
