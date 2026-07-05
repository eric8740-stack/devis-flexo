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

// Phase 2 Lot 4b — édition des 7 coûts ConfigCouts migrés depuis TarifPoste
// (Lot 4a : le moteur ne lit plus TarifPoste pour ces postes). Même mécanique
// que CoutsSection (GET singleton + PUT /api/strategique/couts), mais en
// PUT PARTIEL strict : seuls les champs réellement modifiés sont envoyés.

type CleCoutNumerique = Exclude<
  keyof ConfigCouts,
  "id" | "date_creation" | "date_maj"
>;

export type ChampConfigCouts = {
  key: CleCoutNumerique;
  label: string;
  suffix: string;
  step?: string;
  min?: string;
  max?: string;
  aide?: string;
};

export function ConfigCoutsChamps({
  champs,
  titreToast,
}: {
  champs: ChampConfigCouts[];
  titreToast: string;
}) {
  const { toast } = useToast();
  const [data, setData] = useState<ConfigCouts | null>(null);
  const [initial, setInitial] = useState<ConfigCouts | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getConfigCouts()
      .then((d) => {
        setData(d);
        setInitial(d);
      })
      .catch((e) =>
        toast({ title: "Erreur de chargement", description: String(e), variant: "destructive" })
      );
  }, [toast]);

  if (!data || !initial)
    return <p className="text-sm text-muted-foreground">Chargement…</p>;

  const setField = (key: CleCoutNumerique, value: string) =>
    setData({ ...data, [key]: value === "" ? 0 : Number(value) });

  const handleSave = async () => {
    // PUT partiel : uniquement les champs modifiés depuis le dernier GET/PUT.
    const payload = Object.fromEntries(
      champs
        .filter(({ key }) => data[key] !== initial[key])
        .map(({ key }) => [key, data[key]])
    );
    if (Object.keys(payload).length === 0) {
      toast({ title: "Aucune modification à enregistrer" });
      return;
    }
    setSaving(true);
    try {
      const updated = await updateConfigCouts(payload);
      setData(updated);
      setInitial(updated);
      toast({ title: titreToast });
    } catch (e) {
      toast({ title: "Échec de l'enregistrement", description: String(e), variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {champs.map(({ key, label, suffix, step, min, max, aide }) => (
          <div key={key} className="space-y-1">
            <Label htmlFor={key}>
              {label} <span className="text-muted-foreground">({suffix})</span>
            </Label>
            <Input
              id={key}
              type="number"
              step={step ?? "0.01"}
              min={min ?? "0"}
              max={max}
              value={String(data[key])}
              onChange={(e) => setField(key, e.target.value)}
            />
            {aide ? (
              <p className="text-xs text-muted-foreground">{aide}</p>
            ) : null}
          </div>
        ))}
      </div>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? "Enregistrement…" : "Enregistrer"}
      </Button>
    </div>
  );
}

// --- Section Outils (clichés & outils de découpe) ---------------------------
const CHAMPS_OUTILS: ChampConfigCouts[] = [
  { key: "cliche_prix_couleur_eur", label: "Cliché", suffix: "€/couleur" },
  { key: "outil_base_eur", label: "Outil de découpe (base)", suffix: "€" },
  { key: "outil_par_trace_eur", label: "Outil de découpe", suffix: "€/tracé" },
  {
    key: "surcout_forme_speciale_facteur",
    label: "Surcoût forme spéciale",
    suffix: "facteur ×",
    step: "0.05",
    min: "1",
    max: "10",
    aide: "Multiplicateur du coût outil de base : 1,30 = +30 %. Entre 1 et 10.",
  },
];

export function OutilsCoutsSection() {
  return (
    <ConfigCoutsChamps champs={CHAMPS_OUTILS} titreToast="Coûts outils enregistrés" />
  );
}

// --- Section Calage ----------------------------------------------------------
const CHAMPS_CALAGE: ChampConfigCouts[] = [
  { key: "calage_forfait_eur", label: "Forfait calage", suffix: "€" },
];

export function CalageCoutsSection() {
  return (
    <ConfigCoutsChamps champs={CHAMPS_CALAGE} titreToast="Forfait calage enregistré" />
  );
}

// --- Section Finitions -------------------------------------------------------
const CHAMPS_FINITIONS: ChampConfigCouts[] = [
  { key: "finitions_prix_m2_eur", label: "Finitions", suffix: "€/m²" },
];

export function FinitionsCoutsSection() {
  return (
    <ConfigCoutsChamps champs={CHAMPS_FINITIONS} titreToast="Prix finitions enregistré" />
  );
}

// --- Sous-groupe Roulage (marge de confort) ----------------------------------
const CHAMPS_MARGE_ROULAGE: ChampConfigCouts[] = [
  {
    key: "marge_confort_roulage_mm",
    label: "Marge de confort",
    suffix: "mm",
    step: "1",
    aide: "Entier ≥ 0, ajouté au développement lors du calcul de roulage.",
  },
];

export function MargeRoulageSection() {
  return (
    <ConfigCoutsChamps
      champs={CHAMPS_MARGE_ROULAGE}
      titreToast="Marge de confort enregistrée"
    />
  );
}
