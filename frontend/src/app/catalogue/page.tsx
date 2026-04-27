"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  deleteCatalogueItem,
  listCatalogue,
  type CatalogueItem,
} from "@/lib/api";

const COLUMNS: Column<CatalogueItem>[] = [
  { key: "id", label: "#", className: "w-12" },
  { key: "code_produit", label: "Code" },
  { key: "designation", label: "Désignation" },
  { key: "client_id", label: "Client (ID)" },
  { key: "format_mm", label: "Format" },
  { key: "nb_couleurs", label: "Couleurs" },
  {
    key: "prix_unitaire_eur",
    label: "Prix unit. (€)",
    render: (c) =>
      c.prix_unitaire_eur === null ? "—" : Number(c.prix_unitaire_eur).toFixed(4),
  },
  { key: "frequence_estimee", label: "Fréquence" },
];

export default function CataloguePage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<CatalogueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filterClientId, setFilterClientId] = useState<string>("");

  const load = (clientId?: number) =>
    listCatalogue(clientId)
      .then(setItems)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );

  useEffect(() => {
    load();
  }, []);

  const handleFilter = () => {
    const id = filterClientId.trim() === "" ? undefined : Number(filterClientId);
    setItems(null);
    setError(null);
    load(id);
  };

  const handleDelete = async (item: CatalogueItem) => {
    try {
      await deleteCatalogueItem(item.id);
      toast({
        title: "Produit supprimé",
        description: `« ${item.code_produit} »`,
      });
      const id =
        filterClientId.trim() === "" ? undefined : Number(filterClientId);
      await load(id);
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
          Catalogue produits
        </h1>
        <Button asChild>
          <Link href="/catalogue/nouveau">+ Nouveau produit</Link>
        </Button>
      </div>

      <div className="mb-6 flex items-end gap-2">
        <div className="grid gap-2">
          <Label htmlFor="filter_client">Filtrer par ID client</Label>
          <Input
            id="filter_client"
            type="number"
            placeholder="ex: 1"
            value={filterClientId}
            onChange={(e) => setFilterClientId(e.target.value)}
            className="w-40"
          />
        </div>
        <Button variant="outline" onClick={handleFilter}>
          Filtrer
        </Button>
        {filterClientId && (
          <Button
            variant="ghost"
            onClick={() => {
              setFilterClientId("");
              load();
            }}
          >
            Effacer
          </Button>
        )}
      </div>

      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !items ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={items}
          columns={COLUMNS}
          onEdit={(c) => router.push(`/catalogue/${c.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(c) =>
            `Le produit « ${c.code_produit} » (${c.designation}) va être supprimé. Cette action est irréversible.`
          }
        />
      )}
    </main>
  );
}
