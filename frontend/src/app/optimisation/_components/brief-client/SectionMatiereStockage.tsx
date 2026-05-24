"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  conseilsAdhesif,
  type ConditionsStockage,
} from "@/lib/adhesif-helper";

import {
  type BriefClientData,
  inputValueNum,
  parseNumOrNull,
} from "./types";

interface Props {
  value: BriefClientData;
  onChange: (next: BriefClientData) => void;
}

export function SectionMatiereStockage({ value, onChange }: Props) {
  const setStockage = (patch: Partial<ConditionsStockage>) => {
    onChange({
      ...value,
      conditions_stockage: { ...value.conditions_stockage, ...patch },
    });
  };

  const conseils = conseilsAdhesif(value.conditions_stockage);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Matière &amp; stockage</CardTitle>
        <CardDescription>
          Conditions de stockage du rouleau côté client. Détermine le type
          d&apos;adhésif recommandé (affichage live ci-dessous).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="brief-humidite">Humidité — %</Label>
            <Input
              id="brief-humidite"
              type="number"
              inputMode="decimal"
              min={0}
              max={100}
              step="1"
              placeholder="ex : 50"
              value={inputValueNum(value.conditions_stockage.humidite_pct)}
              onChange={(e) =>
                setStockage({ humidite_pct: parseNumOrNull(e.target.value) })
              }
            />
            <p className="text-xs text-muted-foreground">
              &gt; 70 % → adhésif tropical.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="brief-tmin">T° min — °C</Label>
            <Input
              id="brief-tmin"
              type="number"
              inputMode="decimal"
              step="1"
              placeholder="ex : 5"
              value={inputValueNum(value.conditions_stockage.t_min_c)}
              onChange={(e) =>
                setStockage({ t_min_c: parseNumOrNull(e.target.value) })
              }
            />
            <p className="text-xs text-muted-foreground">
              &lt; 0 °C → adhésif froid négatif.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="brief-tmax">T° max — °C</Label>
            <Input
              id="brief-tmax"
              type="number"
              inputMode="decimal"
              step="1"
              placeholder="ex : 30"
              value={inputValueNum(value.conditions_stockage.t_max_c)}
              onChange={(e) =>
                setStockage({ t_max_c: parseNumOrNull(e.target.value) })
              }
            />
            <p className="text-xs text-muted-foreground">
              &gt; 60 °C → adhésif haute température.
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Lieu de stockage</Label>
          <div className="flex flex-col gap-2 sm:flex-row sm:gap-4">
            {(["interieur", "exterieur"] as const).map((opt) => (
              <label
                key={opt}
                className="flex min-h-[44px] cursor-pointer items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm hover:bg-accent sm:flex-1"
              >
                <input
                  type="radio"
                  name="brief-lieu"
                  value={opt}
                  checked={value.conditions_stockage.lieu === opt}
                  onChange={() => setStockage({ lieu: opt })}
                  className="h-4 w-4 accent-foreground"
                />
                <span>{opt === "interieur" ? "Intérieur" : "Extérieur"}</span>
              </label>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Extérieur → adhésif UV-résistant.
          </p>
        </div>

        <div className="rounded-md border border-blue-200 bg-blue-50 p-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-blue-900">
            Conseil adhésif
          </p>
          <ul className="space-y-1 text-sm text-blue-900">
            {conseils.map((c) => (
              <li key={c}>• {c}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
