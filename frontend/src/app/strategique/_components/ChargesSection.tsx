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
  CATEGORIES_CHARGE,
  type CategorieCharge,
  type ChargeMensuelle,
  createChargeMensuelle,
  deleteChargeMensuelle,
  listChargesMensuelles,
  updateChargeMensuelle,
} from "@/lib/api";

// Onglet Stratégique — Charges (frais fixes mensuels). CRUD inline (table
// éditable + form d'ajout) sur le même modèle que Roulage & Production. La
// page standalone /charges-mensuelles reste accessible séparément.
const VIDE = {
  libelle: "",
  categorie: "loyer" as CategorieCharge,
  montant_eur: 0,
  date_debut: new Date().toISOString().slice(0, 10),
  date_fin: null as string | null,
  commentaire: null as string | null,
};

const selectCls =
  "h-9 w-full rounded-md border border-input bg-background px-2 text-sm";

export function ChargesSection() {
  const { toast } = useToast();
  const [rows, setRows] = useState<ChargeMensuelle[]>([]);
  const [nouveau, setNouveau] = useState({ ...VIDE });

  const recharger = () =>
    listChargesMensuelles()
      .then(setRows)
      .catch((e) =>
        toast({
          title: "Erreur de chargement",
          description: String(e),
          variant: "destructive",
        })
      );

  useEffect(() => {
    recharger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patchRow = (id: number, patch: Partial<ChargeMensuelle>) =>
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  const handleSave = async (row: ChargeMensuelle) => {
    try {
      await updateChargeMensuelle(row.id, {
        libelle: row.libelle,
        categorie: row.categorie,
        montant_eur: Number(row.montant_eur),
        date_debut: row.date_debut,
        date_fin: row.date_fin,
        commentaire: row.commentaire,
      });
      toast({ title: `« ${row.libelle} » enregistré` });
    } catch (e) {
      toast({
        title: "Échec de l'enregistrement",
        description: String(e),
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (row: ChargeMensuelle) => {
    try {
      await deleteChargeMensuelle(row.id);
      setRows((rs) => rs.filter((r) => r.id !== row.id));
      toast({ title: `« ${row.libelle} » supprimé` });
    } catch (e) {
      toast({
        title: "Échec de la suppression",
        description: String(e),
        variant: "destructive",
      });
    }
  };

  const handleCreate = async () => {
    if (!nouveau.libelle.trim()) {
      toast({ title: "Libellé requis", variant: "destructive" });
      return;
    }
    try {
      const created = await createChargeMensuelle({
        ...nouveau,
        montant_eur: Number(nouveau.montant_eur),
      });
      setRows((rs) => [...rs, created]);
      setNouveau({ ...VIDE });
      toast({ title: `« ${created.libelle} » ajouté` });
    } catch (e) {
      toast({
        title: "Échec de l'ajout",
        description: String(e),
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Libellé</TableHead>
            <TableHead>Catégorie</TableHead>
            <TableHead>Montant (€/mois)</TableHead>
            <TableHead>Début</TableHead>
            <TableHead>Fin</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-muted-foreground">
                Aucune charge configurée.
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>
                  <Input
                    aria-label="Libellé"
                    value={row.libelle}
                    onChange={(e) =>
                      patchRow(row.id, { libelle: e.target.value })
                    }
                  />
                </TableCell>
                <TableCell>
                  <select
                    aria-label="Catégorie"
                    className={selectCls}
                    value={row.categorie}
                    onChange={(e) =>
                      patchRow(row.id, {
                        categorie: e.target.value as CategorieCharge,
                      })
                    }
                  >
                    {CATEGORIES_CHARGE.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </TableCell>
                <TableCell>
                  <Input
                    aria-label="Montant"
                    type="number"
                    step="0.01"
                    min="0"
                    value={String(row.montant_eur)}
                    onChange={(e) =>
                      patchRow(row.id, { montant_eur: Number(e.target.value) })
                    }
                  />
                </TableCell>
                <TableCell>
                  <Input
                    aria-label="Début"
                    type="date"
                    value={row.date_debut ?? ""}
                    onChange={(e) =>
                      patchRow(row.id, { date_debut: e.target.value })
                    }
                  />
                </TableCell>
                <TableCell>
                  <Input
                    aria-label="Fin"
                    type="date"
                    value={row.date_fin ?? ""}
                    onChange={(e) =>
                      patchRow(row.id, {
                        date_fin: e.target.value === "" ? null : e.target.value,
                      })
                    }
                  />
                </TableCell>
                <TableCell className="space-x-2 whitespace-nowrap">
                  <Button size="sm" onClick={() => handleSave(row)}>
                    Enregistrer
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDelete(row)}
                  >
                    Supprimer
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <div className="rounded-md border p-4">
        <h3 className="mb-3 text-sm font-medium">Ajouter une charge</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-6 sm:items-end">
          <Input
            aria-label="Nouveau libellé"
            placeholder="Libellé"
            value={nouveau.libelle}
            onChange={(e) =>
              setNouveau({ ...nouveau, libelle: e.target.value })
            }
          />
          <select
            aria-label="Nouvelle catégorie"
            className={selectCls}
            value={nouveau.categorie}
            onChange={(e) =>
              setNouveau({
                ...nouveau,
                categorie: e.target.value as CategorieCharge,
              })
            }
          >
            {CATEGORIES_CHARGE.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <Input
            aria-label="Nouveau montant"
            type="number"
            step="0.01"
            min="0"
            value={String(nouveau.montant_eur)}
            onChange={(e) =>
              setNouveau({ ...nouveau, montant_eur: Number(e.target.value) })
            }
          />
          <Input
            aria-label="Nouvelle date début"
            type="date"
            value={nouveau.date_debut}
            onChange={(e) =>
              setNouveau({ ...nouveau, date_debut: e.target.value })
            }
          />
          <Input
            aria-label="Nouvelle date fin"
            type="date"
            value={nouveau.date_fin ?? ""}
            onChange={(e) =>
              setNouveau({
                ...nouveau,
                date_fin: e.target.value === "" ? null : e.target.value,
              })
            }
          />
          <Button onClick={handleCreate}>Ajouter</Button>
        </div>
      </div>
    </div>
  );
}
