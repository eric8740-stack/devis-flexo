"use client";

import { useRouter } from "next/navigation";

import { OperationFinitionForm } from "@/components/OperationFinitionForm";
import { useToast } from "@/hooks/use-toast";
import {
  createOperationFinition,
  type OperationFinitionCreate,
} from "@/lib/api";

export default function NouvelleOperationPage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: OperationFinitionCreate) => {
    try {
      const created = await createOperationFinition(data);
      toast({ title: "Opération créée", description: `« ${created.nom} »` });
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
      <OperationFinitionForm
        title="Nouvelle opération de finition"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/operations-finition")}
      />
    </main>
  );
}
