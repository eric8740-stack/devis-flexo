"use client";

import { useRouter } from "next/navigation";

import { FournisseurForm } from "@/components/FournisseurForm";
import { useToast } from "@/hooks/use-toast";
import { createFournisseur, type FournisseurCreate } from "@/lib/api";

export default function NouveauFournisseurPage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: FournisseurCreate) => {
    try {
      const created = await createFournisseur(data);
      toast({
        title: "Fournisseur créé",
        description: `« ${created.raison_sociale} » a été ajouté.`,
      });
      router.push("/fournisseurs");
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
      <FournisseurForm
        title="Nouveau fournisseur"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/fournisseurs")}
      />
    </main>
  );
}
