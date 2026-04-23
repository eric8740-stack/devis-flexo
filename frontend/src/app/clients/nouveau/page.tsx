"use client";

import { useRouter } from "next/navigation";

import { ClientForm } from "@/components/ClientForm";
import { useToast } from "@/hooks/use-toast";
import { createClient, type ClientCreate } from "@/lib/api";

export default function NouveauClientPage() {
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: ClientCreate) => {
    try {
      const created = await createClient(data);
      toast({
        title: "Client créé",
        description: `« ${created.raison_sociale} » a été ajouté.`,
      });
      router.push("/clients");
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
      <ClientForm
        title="Nouveau client"
        submitLabel="Créer"
        onSubmit={handleSubmit}
        onCancel={() => router.push("/clients")}
      />
    </main>
  );
}
