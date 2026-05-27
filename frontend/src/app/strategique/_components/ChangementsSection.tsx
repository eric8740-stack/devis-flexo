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
  type ConfigChangements,
  getConfigChangements,
  updateConfigChangements,
} from "@/lib/api";

// Section 6D — Changements (couleur / format / nettoyage). Singleton tenant.
// Source : ConfigChangements (Phase 1). PUT /api/strategique/changements.
const LIGNES: {
  label: string;
  dureeKey: keyof ConfigChangements;
  coutKey: keyof ConfigChangements;
}[] = [
  {
    label: "Changement couleur",
    dureeKey: "changement_couleur_duree_min",
    coutKey: "changement_couleur_cout_eur",
  },
  {
    label: "Changement format",
    dureeKey: "changement_format_duree_min",
    coutKey: "changement_format_cout_eur",
  },
  {
    label: "Nettoyage machine",
    dureeKey: "nettoyage_duree_min",
    coutKey: "nettoyage_cout_eur",
  },
];

export function ChangementsSection() {
  const { toast } = useToast();
  const [data, setData] = useState<ConfigChangements | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getConfigChangements()
      .then(setData)
      .catch((e) =>
        toast({ title: "Erreur de chargement", description: String(e), variant: "destructive" })
      );
  }, [toast]);

  if (!data) return <p className="text-sm text-muted-foreground">Chargement…</p>;

  const setField = (key: keyof ConfigChangements, value: string) =>
    setData({ ...data, [key]: value === "" ? 0 : Number(value) });

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateConfigChangements({
        changement_couleur_duree_min: data.changement_couleur_duree_min,
        changement_couleur_cout_eur: data.changement_couleur_cout_eur,
        changement_format_duree_min: data.changement_format_duree_min,
        changement_format_cout_eur: data.changement_format_cout_eur,
        nettoyage_duree_min: data.nettoyage_duree_min,
        nettoyage_cout_eur: data.nettoyage_cout_eur,
      });
      setData(updated);
      toast({ title: "Changements enregistrés" });
    } catch (e) {
      toast({ title: "Échec de l'enregistrement", description: String(e), variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Type</TableHead>
            <TableHead>Durée (min)</TableHead>
            <TableHead>Coût (€)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {LIGNES.map(({ label, dureeKey, coutKey }) => (
            <TableRow key={label}>
              <TableCell>{label}</TableCell>
              <TableCell>
                <Input
                  aria-label={`${label} durée`}
                  type="number"
                  min="0"
                  value={String(data[dureeKey])}
                  onChange={(e) => setField(dureeKey, e.target.value)}
                />
              </TableCell>
              <TableCell>
                <Input
                  aria-label={`${label} coût`}
                  type="number"
                  step="0.01"
                  min="0"
                  value={String(data[coutKey])}
                  onChange={(e) => setField(coutKey, e.target.value)}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? "Enregistrement…" : "Enregistrer"}
      </Button>
    </div>
  );
}
