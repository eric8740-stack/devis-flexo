"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { deleteClient, listClients, type Client } from "@/lib/api";

const COLUMNS: Column<Client>[] = [
  { key: "id", label: "#", className: "w-12" },
  { key: "raison_sociale", label: "Raison sociale" },
  { key: "segment", label: "Segment" },
  { key: "email", label: "Email" },
  { key: "tel", label: "Téléphone" },
];

export default function ClientsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [clients, setClients] = useState<Client[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // `isCancelled` (audit 05/07/2026 M5) : le useEffect passe un flag lu
  // avant chaque setState pour ignorer une réponse arrivée après unmount.
  const load = (isCancelled: () => boolean = () => false) =>
    listClients()
      .then((res) => {
        if (!isCancelled()) setClients(res);
      })
      .catch((err: unknown) => {
        if (!isCancelled()) {
          setError(err instanceof Error ? err.message : String(err));
        }
      });

  useEffect(() => {
    let cancelled = false;
    void load(() => cancelled);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (c: Client) => {
    try {
      await deleteClient(c.id);
      toast({
        title: "Client supprimé",
        description: `« ${c.raison_sociale} » a été supprimé.`,
      });
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  return (
    <main className="container mx-auto max-w-5xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Clients</h1>
        <Button asChild>
          <Link href="/clients/nouveau">+ Nouveau client</Link>
        </Button>
      </div>

      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !clients ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={clients}
          columns={COLUMNS}
          onEdit={(c) => router.push(`/clients/${c.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(c) =>
            `Le client « ${c.raison_sociale} » va être supprimé. Cette action est irréversible.`
          }
        />
      )}
    </main>
  );
}
