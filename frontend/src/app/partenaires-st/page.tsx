"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  deletePartenaireST,
  listPartenairesST,
  reactiverPartenaireST,
  type PartenaireST,
} from "@/lib/api";

export default function PartenairesSTPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<PartenaireST[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeInactives, setIncludeInactives] = useState(false);

  const load = useCallback(
    () =>
      listPartenairesST(includeInactives)
        .then(setItems)
        .catch((err: unknown) =>
          setError(err instanceof Error ? err.message : String(err))
        ),
    [includeInactives]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (p: PartenaireST) => {
    try {
      await deletePartenaireST(p.id);
      toast({
        title: "Partenaire désactivé",
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

  const handleReactiver = async (p: PartenaireST) => {
    try {
      await reactiverPartenaireST(p.id);
      toast({
        title: "Partenaire réactivé",
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

  const columns: Column<PartenaireST>[] = [
    { key: "id", label: "#", className: "w-12" },
    { key: "raison_sociale", label: "Raison sociale" },
    { key: "prestation_type", label: "Prestation" },
    { key: "delai_jours_moyen", label: "Délai (j)" },
    { key: "qualite_score", label: "Qualité (1-5)" },
    {
      key: "actif",
      label: "Statut",
      render: (p) =>
        p.actif ? (
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
                void handleReactiver(p);
              }}
            >
              Réactiver
            </Button>
          </span>
        ),
    },
  ];

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
      <label className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={includeInactives}
          onChange={(e) => setIncludeInactives(e.target.checked)}
          className="h-4 w-4"
        />
        Afficher les partenaires inactifs
      </label>
      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !items ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={items}
          columns={columns}
          onEdit={(p) => router.push(`/partenaires-st/${p.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(p) =>
            `Le partenaire « ${p.raison_sociale} » va être désactivé. Il ne sera plus proposé dans les nouveaux devis mais reste réactivable.`
          }
        />
      )}
    </main>
  );
}
