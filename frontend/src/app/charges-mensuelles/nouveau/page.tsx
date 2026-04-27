"use client";

import { useRouter } from "next/navigation";

import { ChargeMensuelleForm } from "@/components/ChargeMensuelleForm";
import { useToast } from "@/hooks/use-toast";
import {
  createChargeMensuelle,
  type ChargeMensuelleCreate,
} from "@/lib/api";

export default function NouvelleChargePage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: ChargeMensuelleCreate) => {
    try {
      const created = await createChargeMensuelle(data);
      toast({ title: "Charge créée", description: `« ${created.libelle} »` });
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
      <ChargeMensuelleForm
        title="Nouvelle charge mensuelle"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/charges-mensuelles")}
      />
    </main>
  );
}
