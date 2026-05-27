"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  type ConfigCouts,
  getConfigCouts,
  updateConfigCouts,
} from "@/lib/api";

// Section 6 A/B/C — Coûts variables + fixes + marges (singleton tenant).
// Source : ConfigCouts (Phase 1). PUT partiel /api/strategique/couts.
const CHAMPS: { key: keyof ConfigCouts; label: string; suffix: string }[] = [
  { key: "cout_exploitation_machine_eur_h", label: "Exploitation machine", suffix: "€/h" },
  { key: "cout_operateur_eur_h", label: "Opérateur", suffix: "€/h" },
  { key: "cout_energies_eur_h", label: "Énergie", suffix: "€/h" },
  { key: "cout_fixe_atelier_eur_mois", label: "Atelier (fixe)", suffix: "€/mois" },
  { key: "cout_fixe_maintenance_eur_mois", label: "Maintenance (fixe)", suffix: "€/mois" },
  { key: "marge_standard_pct", label: "Marge standard", suffix: "%" },
  { key: "buffer_rebut_pct", label: "Buffer rebut", suffix: "%" },
  { key: "buffer_setup_pct", label: "Buffer setup", suffix: "%" },
];

export function CoutsSection() {
  const { toast } = useToast();
  const [data, setData] = useState<ConfigCouts | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getConfigCouts()
      .then(setData)
      .catch((e) =>
        toast({ title: "Erreur de chargement", description: String(e), variant: "destructive" })
      );
  }, [toast]);

  if (!data) return <p className="text-sm text-muted-foreground">Chargement…</p>;

  const setField = (key: keyof ConfigCouts, value: string) =>
    setData({ ...data, [key]: value === "" ? 0 : Number(value) });

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = Object.fromEntries(
        CHAMPS.map(({ key }) => [key, data[key]])
      );
      const updated = await updateConfigCouts(payload);
      setData(updated);
      toast({ title: "Coûts & marges enregistrés" });
    } catch (e) {
      toast({ title: "Échec de l'enregistrement", description: String(e), variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {CHAMPS.map(({ key, label, suffix }) => (
          <div key={key} className="space-y-1">
            <Label htmlFor={key}>
              {label} <span className="text-muted-foreground">({suffix})</span>
            </Label>
            <Input
              id={key}
              type="number"
              step="0.01"
              min="0"
              value={String(data[key])}
              onChange={(e) => setField(key, e.target.value)}
            />
          </div>
        ))}
      </div>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? "Enregistrement…" : "Enregistrer"}
      </Button>
    </div>
  );
}
