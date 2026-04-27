"use client";

import { useRouter } from "next/navigation";

import { CatalogueForm } from "@/components/CatalogueForm";
import { useToast } from "@/hooks/use-toast";
import { createCatalogueItem, type CatalogueCreate } from "@/lib/api";

export default function NouveauProduitCataloguePage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: CatalogueCreate) => {
    try {
      const created = await createCatalogueItem(data);
      toast({
        title: "Produit ajouté au catalogue",
        description: `« ${created.code_produit} »`,
      });
      router.push("/catalogue");
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
      <CatalogueForm
        title="Nouveau produit catalogue"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/catalogue")}
      />
    </main>
  );
}
