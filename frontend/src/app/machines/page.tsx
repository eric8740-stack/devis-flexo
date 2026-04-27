"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { deleteMachine, listMachines, type Machine } from "@/lib/api";

const COLUMNS: Column<Machine>[] = [
  { key: "id", label: "#", className: "w-12" },
  { key: "nom", label: "Nom" },
  { key: "statut", label: "Statut" },
  { key: "nb_couleurs", label: "Nb couleurs" },
  { key: "vitesse_max_m_min", label: "Vitesse (m/min)" },
  { key: "cout_horaire_eur", label: "Coût horaire (€)" },
];

export default function MachinesPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<Machine[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    listMachines()
      .then(setItems)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (m: Machine) => {
    try {
      await deleteMachine(m.id);
      toast({ title: "Machine supprimée", description: `« ${m.nom} »` });
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
        <h1 className="text-2xl font-semibold tracking-tight">Machines</h1>
        <Button asChild>
          <Link href="/machines/nouveau">+ Nouvelle machine</Link>
        </Button>
      </div>
      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !items ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={items}
          columns={COLUMNS}
          onEdit={(m) => router.push(`/machines/${m.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(m) =>
            `La machine « ${m.nom} » va être supprimée. Cette action est irréversible.`
          }
        />
      )}
    </main>
  );
}
