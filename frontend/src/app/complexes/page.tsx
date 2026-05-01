"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  deleteComplexe,
  listComplexes,
  reactiverComplexe,
  type Complexe,
} from "@/lib/api";

export default function ComplexesPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<Complexe[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeInactives, setIncludeInactives] = useState(false);

  const load = useCallback(
    () =>
      listComplexes(includeInactives)
        .then(setItems)
        .catch((err: unknown) =>
          setError(err instanceof Error ? err.message : String(err))
        ),
    [includeInactives]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (c: Complexe) => {
    try {
      await deleteComplexe(c.id);
      toast({ title: "Complexe désactivé", description: `« ${c.reference} »` });
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const handleReactiver = async (c: Complexe) => {
    try {
      await reactiverComplexe(c.id);
      toast({ title: "Complexe réactivé", description: `« ${c.reference} »` });
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const columns: Column<Complexe>[] = [
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
    {
      key: "actif",
      label: "Statut",
      render: (c) =>
        c.actif ? (
          <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800">
            Actif
          </span>
        ) : (
          <span className="inline-flex items-center gap-2">
            <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              Inactif
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                void handleReactiver(c);
              }}
            >
              Réactiver
            </Button>
          </span>
        ),
    },
  ];

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
      <label className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={includeInactives}
          onChange={(e) => setIncludeInactives(e.target.checked)}
          className="h-4 w-4"
        />
        Afficher les complexes inactifs
      </label>
      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !items ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={items}
          columns={columns}
          onEdit={(c) => router.push(`/complexes/${c.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(c) =>
            `Le complexe « ${c.reference} » va être désactivé. Il ne sera plus proposé dans les nouveaux devis mais reste réactivable.`
          }
        />
      )}
    </main>
  );
}
