"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { deleteComplexe, listComplexes, type Complexe } from "@/lib/api";

const COLUMNS: Column<Complexe>[] = [
  { key: "id", label: "#", className: "w-12" },
  { key: "reference", label: "Référence" },
  { key: "famille", label: "Famille" },
  { key: "grammage_g_m2", label: "Grammage" },
  {
    key: "prix_m2_eur",
    label: "Prix €/m²",
    render: (c) => Number(c.prix_m2_eur).toFixed(4),
  },
  { key: "fournisseur_id", label: "Fournisseur (ID)" },
  { key: "statut", label: "Statut" },
];

export default function ComplexesPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<Complexe[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    listComplexes()
      .then(setItems)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (c: Complexe) => {
    try {
      await deleteComplexe(c.id);
      toast({ title: "Complexe supprimé", description: `« ${c.reference} »` });
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
    <main className="container mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">
          Complexes adhésifs
        </h1>
        <Button asChild>
          <Link href="/complexes/nouveau">+ Nouveau complexe</Link>
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
          onEdit={(c) => router.push(`/complexes/${c.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(c) =>
            `Le complexe « ${c.reference} » va être supprimé. Cette action est irréversible.`
          }
        />
      )}
    </main>
  );
}
