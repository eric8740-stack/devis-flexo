"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ClientForm } from "@/components/ClientForm";
import { useToast } from "@/hooks/use-toast";
import {
  getClient,
  updateClient,
  type Client,
  type ClientCreate,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditClientPage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [client, setClient] = useState<Client | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getClient(id)
      .then(setClient)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: ClientCreate) => {
    try {
      const updated = await updateClient(id, data);
      toast({
        title: "Client mis à jour",
        description: `« ${updated.raison_sociale} » a été enregistré.`,
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
      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !client ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <ClientForm
          title={`Client #${client.id}`}
          submitLabel="Enregistrer"
          initial={extractClientCreate(client)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/clients")}
        />
      )}
    </main>
  );
}

function extractClientCreate(c: Client): ClientCreate {
  const { id: _id, ...rest } = c;
  void _id;
  return rest;
}
