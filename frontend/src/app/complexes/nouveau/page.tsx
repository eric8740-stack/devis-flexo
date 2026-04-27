"use client";

import { useRouter } from "next/navigation";

import { ComplexeForm } from "@/components/ComplexeForm";
import { useToast } from "@/hooks/use-toast";
import { createComplexe, type ComplexeCreate } from "@/lib/api";

export default function NouveauComplexePage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: ComplexeCreate) => {
    try {
      const created = await createComplexe(data);
      toast({
        title: "Complexe créé",
        description: `« ${created.reference} »`,
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
      <ComplexeForm
        title="Nouveau complexe"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/complexes")}
      />
    </main>
  );
}
