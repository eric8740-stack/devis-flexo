"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FournisseurForm } from "@/components/FournisseurForm";
import { useToast } from "@/hooks/use-toast";
import {
  getFournisseur,
  updateFournisseur,
  type Fournisseur,
  type FournisseurCreate,
} from "@/lib/api";

interface Props {
  params: { id: string };
}

export default function EditFournisseurPage({ params }: Props) {
  const id = Number(params.id);
  const router = useRouter();
  const { toast } = useToast();
  const [fournisseur, setFournisseur] = useState<Fournisseur | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFournisseur(id)
      .then(setFournisseur)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, [id]);

  const handleSubmit = async (data: FournisseurCreate) => {
    try {
      const updated = await updateFournisseur(id, data);
      toast({
        title: "Fournisseur mis à jour",
        description: `« ${updated.raison_sociale} » a été enregistré.`,
      });
      router.push("/fournisseurs");
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
      ) : !fournisseur ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <FournisseurForm
          title={`Fournisseur #${fournisseur.id}`}
          submitLabel="Enregistrer"
          initial={extractCreate(fournisseur)}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/fournisseurs")}
        />
      )}
    </main>
  );
}

function extractCreate(f: Fournisseur): FournisseurCreate {
  const { id: _id, ...rest } = f;
  void _id;
  return rest;
}
