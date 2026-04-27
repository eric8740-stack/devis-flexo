"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CatalogueForm } from "@/components/CatalogueForm";
import { useToast } from "@/hooks/use-toast";
import {
  getCatalogueItem,
  updateCatalogueItem,
  type CatalogueCreate,
  type CatalogueItem,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditCataloguePage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [item, setItem] = useState<CatalogueItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCatalogueItem(id)
      .then(setItem)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: CatalogueCreate) => {
    try {
      const updated = await updateCatalogueItem(id, data);
      toast({
        title: "Produit mis à jour",
        description: `« ${updated.code_produit} »`,
      });
      router.push("/catalogue");
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
      ) : !item ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <CatalogueForm
          title={`Produit #${item.id} — ${item.code_produit}`}
          submitLabel="Enregistrer"
          initial={extractCreate(item)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/catalogue")}
        />
      )}
    </main>
  );
}

function extractCreate(c: CatalogueItem): CatalogueCreate {
  const { id: _id, date_creation: _dc, date_maj: _dm, ...rest } = c;
  void _id;
  void _dc;
  void _dm;
  return {
    ...rest,
    prix_unitaire_eur:
      rest.prix_unitaire_eur === null ? null : Number(rest.prix_unitaire_eur),
  };
}
