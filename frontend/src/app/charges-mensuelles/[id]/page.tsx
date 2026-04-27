"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ChargeMensuelleForm } from "@/components/ChargeMensuelleForm";
import { useToast } from "@/hooks/use-toast";
import {
  getChargeMensuelle,
  updateChargeMensuelle,
  type ChargeMensuelle,
  type ChargeMensuelleCreate,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditChargePage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [item, setItem] = useState<ChargeMensuelle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getChargeMensuelle(id)
      .then(setItem)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: ChargeMensuelleCreate) => {
    try {
      const updated = await updateChargeMensuelle(id, data);
      toast({
        title: "Charge mise à jour",
        description: `« ${updated.libelle} »`,
      });
      router.push("/charges-mensuelles");
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
        <ChargeMensuelleForm
          title={`Charge #${item.id}`}
          submitLabel="Enregistrer"
          initial={extractCreate(item)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/charges-mensuelles")}
        />
      )}
    </main>
  );
}

function extractCreate(c: ChargeMensuelle): ChargeMensuelleCreate {
  const { id: _id, date_creation: _dc, date_maj: _dm, ...rest } = c;
  void _id;
  void _dc;
  void _dm;
  return {
    ...rest,
    montant_eur: Number(rest.montant_eur),
  };
}
