"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PartenaireSTForm } from "@/components/PartenaireSTForm";
import { useToast } from "@/hooks/use-toast";
import {
  getPartenaireST,
  updatePartenaireST,
  type PartenaireST,
  type PartenaireSTCreate,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditPartenairePage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [item, setItem] = useState<PartenaireST | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPartenaireST(id)
      .then(setItem)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: PartenaireSTCreate) => {
    try {
      const updated = await updatePartenaireST(id, data);
      toast({
        title: "Partenaire mis à jour",
        description: `« ${updated.raison_sociale} »`,
      });
      router.push("/partenaires-st");
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
        <PartenaireSTForm
          title={`Partenaire #${item.id}`}
          submitLabel="Enregistrer"
          initial={extractCreate(item)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/partenaires-st")}
        />
      )}
    </main>
  );
}

function extractCreate(p: PartenaireST): PartenaireSTCreate {
  const { id: _id, date_creation: _dc, date_maj: _dm, ...rest } = p;
  void _id;
  void _dc;
  void _dm;
  return rest;
}
