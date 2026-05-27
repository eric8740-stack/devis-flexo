"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import {
  type ConfigRoulage,
  type ModeRoulage,
  MODES_ROULAGE,
  createConfigRoulage,
  deleteConfigRoulage,
  listConfigRoulage,
  updateConfigRoulage,
} from "@/lib/api";

// Section 5 — Roulage & Production (par format). Source : ConfigRoulage
// (Phase 1). CRUD complet /api/strategique/roulage. Le temps de setup/calage
// n'est PAS ici (Machine.duree_calage_h + TarifPoste.calage_forfait).
const VIDE = {
  format_libelle: "",
  mode_roulage: "helicoidal" as ModeRoulage,
  debit_mm_s: 250,
  rebut_pct: 3,
};

export function RoulageSection() {
  const { toast } = useToast();
  const [rows, setRows] = useState<ConfigRoulage[]>([]);
  const [nouveau, setNouveau] = useState({ ...VIDE });

  const recharger = () =>
    listConfigRoulage()
      .then(setRows)
      .catch((e) =>
        toast({ title: "Erreur de chargement", description: String(e), variant: "destructive" })
      );

  useEffect(() => {
    recharger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patchRow = (id: number, patch: Partial<ConfigRoulage>) =>
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  const handleSave = async (row: ConfigRoulage) => {
    try {
      await updateConfigRoulage(row.id, {
        format_libelle: row.format_libelle,
        mode_roulage: row.mode_roulage,
        debit_mm_s: row.debit_mm_s,
        rebut_pct: row.rebut_pct,
      });
      toast({ title: `Format ${row.format_libelle} enregistré` });
    } catch (e) {
      toast({ title: "Échec de l'enregistrement", description: String(e), variant: "destructive" });
    }
  };

  const handleDelete = async (row: ConfigRoulage) => {
    try {
      await deleteConfigRoulage(row.id);
      setRows((rs) => rs.filter((r) => r.id !== row.id));
      toast({ title: `Format ${row.format_libelle} supprimé` });
    } catch (e) {
      toast({ title: "Échec de la suppression", description: String(e), variant: "destructive" });
    }
  };

  const handleCreate = async () => {
    if (!nouveau.format_libelle.trim()) {
      toast({ title: "Format requis", variant: "destructive" });
      return;
    }
    try {
      const created = await createConfigRoulage(nouveau);
      setRows((rs) => [...rs, created]);
      setNouveau({ ...VIDE });
      toast({ title: `Format ${created.format_libelle} ajouté` });
    } catch (e) {
      toast({ title: "Échec de l'ajout", description: String(e), variant: "destructive" });
    }
  };

  const selectCls =
    "h-9 w-full rounded-md border border-input bg-background px-2 text-sm";

  return (
    <div className="space-y-6">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Format</TableHead>
            <TableHead>Mode roulage</TableHead>
            <TableHead>Débit (mm/s)</TableHead>
            <TableHead>Rebut (%)</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} className="text-muted-foreground">
                Aucun format configuré.
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>
                  <Input
                    aria-label="Format"
                    value={row.format_libelle}
                    onChange={(e) => patchRow(row.id, { format_libelle: e.target.value })}
                  />
                </TableCell>
                <TableCell>
                  <select
                    aria-label="Mode roulage"
                    className={selectCls}
                    value={row.mode_roulage}
                    onChange={(e) =>
                      patchRow(row.id, { mode_roulage: e.target.value as ModeRoulage })
                    }
                  >
                    {MODES_ROULAGE.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </TableCell>
                <TableCell>
                  <Input
                    aria-label="Débit"
                    type="number"
                    min="1"
                    value={String(row.debit_mm_s)}
                    onChange={(e) =>
                      patchRow(row.id, { debit_mm_s: Number(e.target.value) })
                    }
                  />
                </TableCell>
                <TableCell>
                  <Input
                    aria-label="Rebut"
                    type="number"
                    step="0.1"
                    min="0"
                    value={String(row.rebut_pct)}
                    onChange={(e) =>
                      patchRow(row.id, { rebut_pct: Number(e.target.value) })
                    }
                  />
                </TableCell>
                <TableCell className="space-x-2 whitespace-nowrap">
                  <Button size="sm" onClick={() => handleSave(row)}>
                    Enregistrer
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleDelete(row)}>
                    Supprimer
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <div className="rounded-md border p-4">
        <h3 className="mb-3 text-sm font-medium">Ajouter un format</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-5 sm:items-end">
          <Input
            aria-label="Nouveau format"
            placeholder="Format (ex: A5)"
            value={nouveau.format_libelle}
            onChange={(e) => setNouveau({ ...nouveau, format_libelle: e.target.value })}
          />
          <select
            aria-label="Nouveau mode"
            className={selectCls}
            value={nouveau.mode_roulage}
            onChange={(e) =>
              setNouveau({ ...nouveau, mode_roulage: e.target.value as ModeRoulage })
            }
          >
            {MODES_ROULAGE.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <Input
            aria-label="Nouveau débit"
            type="number"
            min="1"
            value={String(nouveau.debit_mm_s)}
            onChange={(e) => setNouveau({ ...nouveau, debit_mm_s: Number(e.target.value) })}
          />
          <Input
            aria-label="Nouveau rebut"
            type="number"
            step="0.1"
            min="0"
            value={String(nouveau.rebut_pct)}
            onChange={(e) => setNouveau({ ...nouveau, rebut_pct: Number(e.target.value) })}
          />
          <Button onClick={handleCreate}>Ajouter</Button>
        </div>
      </div>
    </div>
  );
}
