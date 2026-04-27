"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  deleteOperationFinition,
  listOperationsFinition,
  type OperationFinition,
} from "@/lib/api";

const COLUMNS: Column<OperationFinition>[] = [
  { key: "id", label: "#", className: "w-12" },
  { key: "nom", label: "Nom" },
  { key: "unite_facturation", label: "Unité" },
  { key: "cout_unitaire_eur", label: "Coût unit. (€)" },
  { key: "temps_minutes_unite", label: "Temps (min/u)" },
  { key: "statut", label: "Statut" },
];

export default function OperationsFinitionPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<OperationFinition[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    listOperationsFinition()
      .then(setItems)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (op: OperationFinition) => {
    try {
      await deleteOperationFinition(op.id);
      toast({ title: "Opération supprimée", description: `« ${op.nom} »` });
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
        <h1 className="text-2xl font-semibold tracking-tight">
          Opérations de finition
        </h1>
        <Button asChild>
          <Link href="/operations-finition/nouveau">+ Nouvelle opération</Link>
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
          onEdit={(op) => router.push(`/operations-finition/${op.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(op) =>
            `L'opération « ${op.nom} » va être supprimée. Cette action est irréversible.`
          }
        />
      )}
    </main>
  );
}
