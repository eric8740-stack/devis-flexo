"use client";

import { useRouter } from "next/navigation";

import { PartenaireSTForm } from "@/components/PartenaireSTForm";
import { useToast } from "@/hooks/use-toast";
import { createPartenaireST, type PartenaireSTCreate } from "@/lib/api";

export default function NouveauPartenairePage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: PartenaireSTCreate) => {
    try {
      const created = await createPartenaireST(data);
      toast({
        title: "Partenaire créé",
        description: `« ${created.raison_sociale} »`,
      });
      router.push("/partenaires-st");
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
      <PartenaireSTForm
        title="Nouveau partenaire"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/partenaires-st")}
      />
    </main>
  );
}
