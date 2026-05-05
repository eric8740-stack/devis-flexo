"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { MachinesHelp } from "@/components/help/content/MachinesHelp";
import { HelpButton } from "@/components/help/HelpButton";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  deleteMachine,
  listMachines,
  reactiverMachine,
  type Machine,
} from "@/lib/api";

export default function MachinesPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [items, setItems] = useState<Machine[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeInactives, setIncludeInactives] = useState(false);

  const load = useCallback(
    () =>
      listMachines(includeInactives)
        .then(setItems)
        .catch((err: unknown) =>
          setError(err instanceof Error ? err.message : String(err))
        ),
    [includeInactives]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (m: Machine) => {
    try {
      await deleteMachine(m.id);
      toast({ title: "Machine désactivée", description: `« ${m.nom} »` });
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const handleReactiver = async (m: Machine) => {
    try {
      await reactiverMachine(m.id);
      toast({ title: "Machine réactivée", description: `« ${m.nom} »` });
      await load();
    } catch (err) {
      toast({
        title: "Erreur",
        description: err instanceof Error ? err.message : "Erreur inconnue",
        variant: "destructive",
      });
    }
  };

  const columns: Column<Machine>[] = [
    { key: "id", label: "#", className: "w-12" },
    { key: "nom", label: "Nom" },
    {
      key: "actif",
      label: "Statut",
      render: (m) =>
        m.actif ? (
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
                void handleReactiver(m);
              }}
            >
              Réactiver
            </Button>
          </span>
        ),
    },
    { key: "nb_couleurs", label: "Nb couleurs" },
    {
      // Mini-fix vitesse-machine 05/05/2026 : on affiche la VRAIE vitesse
      // utilisée par le moteur (vitesse_moyenne_m_h ÷ 60), pas la valeur
      // catalogue indicative `vitesse_max_m_min` qui n'impacte pas le calcul.
      key: "vitesse_moyenne_m_h",
      label: "Vitesse (m/min)",
      render: (m) =>
        m.vitesse_moyenne_m_h != null
          ? Math.round(m.vitesse_moyenne_m_h / 60)
          : "—",
    },
    { key: "cout_horaire_eur", label: "Coût horaire (€)" },
  ];

  return (
    <main className="container mx-auto max-w-5xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">Machines</h1>
          <HelpButton title="Machines">
            <MachinesHelp />
          </HelpButton>
        </div>
        <Button asChild>
          <Link href="/machines/nouveau">+ Nouvelle machine</Link>
        </Button>
      </div>
      <label className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={includeInactives}
          onChange={(e) => setIncludeInactives(e.target.checked)}
          className="h-4 w-4"
        />
        Afficher les machines inactives
      </label>
      {error ? (
        <p className="text-sm text-red-600">Erreur : {error}</p>
      ) : !items ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <DataTable
          data={items}
          columns={columns}
          onEdit={(m) => router.push(`/machines/${m.id}`)}
          onDelete={handleDelete}
          deleteConfirmLabel={(m) =>
            `La machine « ${m.nom} » va être désactivée (soft delete). Elle ne sera plus proposée dans les nouveaux devis mais reste réactivable.`
          }
        />
      )}
    </main>
  );
}
