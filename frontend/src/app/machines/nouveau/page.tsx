"use client";

import { useRouter } from "next/navigation";

import { MachineForm } from "@/components/MachineForm";
import { useToast } from "@/hooks/use-toast";
import { createMachine, type MachineCreate } from "@/lib/api";

export default function NouvelleMachinePage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: MachineCreate) => {
    try {
      const created = await createMachine(data);
      toast({ title: "Machine créée", description: `« ${created.nom} »` });
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
      <MachineForm
        title="Nouvelle machine"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/machines")}
      />
    </main>
  );
}
