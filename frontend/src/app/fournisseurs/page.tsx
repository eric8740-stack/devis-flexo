"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  deleteFournisseur,
  listFournisseurs,
  type Fournisseur,
} from "@/lib/api";

const COLUMNS: Column<Fournisseur>[] = [
  { key: "id", label: "#", className: "w-12" },
  { key: "raison_sociale", label: "Raison sociale" },
  { key: "categorie", label: "Catégorie" },
  { key: "email", label: "Email" },
  { key: "tel", label: "Téléphone" },
];

export default function FournisseursPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [fournisseurs, setFournisseurs] = useState<Fournisseur[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    listFournisseurs()
      .then(setFournisseurs)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (f: Fournisseur) => {
    try {
      await deleteFournisseur(f.id);
      toast({
        title: "Fournisseur supprimé",
        description: `« ${f.raison_sociale} » a été supprimé.`,
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
        <h1 className="text-2xl font-semibold tracking-tight">Fournisseurs</h1>
        <Button asChild>
          <Link href="/fournisseurs/nouveau">+ Nouveau fournisseur</Link>
        </Button>
      </div>

      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !fournisseurs ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={fournisseurs}
          columns={COLUMNS}
          onEdit={(f) => router.push(`/fournisseurs/${f.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(f) =>
            `Le fournisseur « ${f.raison_sociale} » va être supprimé. Cette action est irréversible.`
          }
        />
      )}
    </main>
  );
}
