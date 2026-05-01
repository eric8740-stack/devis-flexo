"use client";

import { useCallback, useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { OutilDecoupeForm } from "@/components/OutilDecoupeForm";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  createOutilDecoupe,
  deleteOutilDecoupe,
  listOutilsDecoupe,
  reactiverOutilDecoupe,
  updateOutilDecoupe,
  type OutilDecoupeCreate,
  type OutilDecoupeRead,
} from "@/lib/api";

type FormMode = "create" | "edit" | null;

export default function ParametresOutilsPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<OutilDecoupeRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeInactives, setIncludeInactives] = useState(false);
  const [mode, setMode] = useState<FormMode>(null);
  const [editing, setEditing] = useState<OutilDecoupeRead | null>(null);

  const load = useCallback(
    () =>
      listOutilsDecoupe(includeInactives)
        .then(setItems)
        .catch((err: unknown) =>
          setError(err instanceof Error ? err.message : String(err))
        ),
    [includeInactives]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async (data: OutilDecoupeCreate) => {
    try {
      await createOutilDecoupe(data);
      toast({ title: "Outil créé", description: `« ${data.libelle} »` });
      setMode(null);
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const handleUpdate = async (data: OutilDecoupeCreate) => {
    if (!editing) return;
    try {
      await updateOutilDecoupe(editing.id, data);
      toast({ title: "Outil mis à jour", description: `« ${data.libelle} »` });
      setMode(null);
      setEditing(null);
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (o: OutilDecoupeRead) => {
    try {
      await deleteOutilDecoupe(o.id);
      toast({ title: "Outil désactivé", description: `« ${o.libelle} »` });
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const handleReactiver = async (o: OutilDecoupeRead) => {
    try {
      await reactiverOutilDecoupe(o.id);
      toast({ title: "Outil réactivé", description: `« ${o.libelle} »` });
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const columns: Column<OutilDecoupeRead>[] = [
    { key: "id", label: "#", className: "w-12" },
    { key: "libelle", label: "Libellé" },
    {
      key: "format",
      label: "Format (l × h mm)",
      render: (o) => `${o.format_l_mm} × ${o.format_h_mm}`,
    },
    {
      key: "poses",
      label: "Poses (l × dvp)",
      render: (o) => `${o.nb_poses_l} × ${o.nb_poses_h}`,
    },
    {
      key: "forme_speciale",
      label: "Forme",
      render: (o) => (o.forme_speciale ? "spéciale" : "standard"),
    },
    {
      key: "actif",
      label: "Statut",
      render: (o) =>
        o.actif ? (
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
                void handleReactiver(o);
              }}
            >
              Réactiver
            </Button>
          </span>
        ),
    },
  ];

  if (mode === "create") {
    return (
      <OutilDecoupeForm
        title="Nouvel outil de découpe"
        onSubmit={handleCreate}
        onCancel={() => setMode(null)}
      />
    );
  }
  if (mode === "edit" && editing) {
    const initial: OutilDecoupeCreate = {
      libelle: editing.libelle,
      format_l_mm: editing.format_l_mm,
      format_h_mm: editing.format_h_mm,
      nb_poses_l: editing.nb_poses_l,
      nb_poses_h: editing.nb_poses_h,
      forme_speciale: editing.forme_speciale,
      actif: editing.actif,
    };
    return (
      <OutilDecoupeForm
        title={`Édition — ${editing.libelle}`}
        initial={initial}
        onSubmit={handleUpdate}
        onCancel={() => {
          setMode(null);
          setEditing(null);
        }}
        submitLabel="Mettre à jour"
      />
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Catalogue des outils de découpe (cylindres magnétiques équipés).
        </p>
        <Button type="button" onClick={() => setMode("create")}>
          + Ajouter
        </Button>
      </div>
      <label className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={includeInactives}
          onChange={(e) => setIncludeInactives(e.target.checked)}
          className="h-4 w-4"
        />
        Afficher les outils inactifs
      </label>
      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !items ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={items}
          columns={columns}
          onEdit={(o) => {
            setEditing(o);
            setMode("edit");
          }}
          onDelete={handleDelete}
          deleteConfirmLabel={(o) =>
            `L'outil « ${o.libelle} » va être désactivé. Il ne sera plus proposé dans les nouveaux devis mais reste réactivable.`
          }
        />
      )}
    </div>
  );
}
