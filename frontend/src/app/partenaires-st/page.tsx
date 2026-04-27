"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  deletePartenaireST,
  listPartenairesST,
  type PartenaireST,
} from "@/lib/api";

const COLUMNS: Column<PartenaireST>[] = [
  { key: "id", label: "#", className: "w-12" },
  { key: "raison_sociale", label: "Raison sociale" },
  { key: "prestation_type", label: "Prestation" },
  { key: "delai_jours_moyen", label: "Délai (j)" },
  { key: "qualite_score", label: "Qualité (1-5)" },
  { key: "statut", label: "Statut" },
];

export default function PartenairesSTPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<PartenaireST[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () =>
    listPartenairesST()
      .then(setItems)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (p: PartenaireST) => {
    try {
      await deletePartenaireST(p.id);
      toast({
        title: "Partenaire supprimé",
        description: `« ${p.raison_sociale} »`,
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
        <h1 className="text-2xl font-semibold tracking-tight">
          Partenaires sous-traitance
        </h1>
        <Button asChild>
          <Link href="/partenaires-st/nouveau">+ Nouveau partenaire</Link>
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
          onEdit={(p) => router.push(`/partenaires-st/${p.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(p) =>
            `Le partenaire « ${p.raison_sociale} » va être supprimé. Cette action est irréversible.`
          }
        />
      )}
    </main>
  );
}
