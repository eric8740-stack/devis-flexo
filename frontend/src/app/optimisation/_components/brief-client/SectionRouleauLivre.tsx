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
  type BriefClientData,
  inputValueNum,
  parseNumOrNull,
} from "./types";

interface Props {
  value: BriefClientData;
  onChange: (next: BriefClientData) => void;
}

export function SectionRouleauLivre({ value, onChange }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Rouleau livré</CardTitle>
        <CardDescription>
          Caractéristiques de la livraison finale au client : nombre
          d&apos;étiquettes par rouleau, encombrement bobine, nb de fronts en
          sortie machine.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="brief-nb-etiq-rouleau">
              Nb étiquettes par rouleau
            </Label>
            <Input
              id="brief-nb-etiq-rouleau"
              type="number"
              inputMode="numeric"
              min={1}
              placeholder="ex : 1000"
              value={inputValueNum(value.nb_etiquettes_par_rouleau)}
              onChange={(e) =>
                onChange({
                  ...value,
                  nb_etiquettes_par_rouleau: parseNumOrNull(e.target.value),
                })
              }
            />
            <p className="text-xs text-muted-foreground">
              Optionnel — laisser vide si standard de l&apos;imprimerie.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="brief-diam-max">Diamètre maxi bobine — mm</Label>
            <Input
              id="brief-diam-max"
              type="number"
              inputMode="numeric"
              min={1}
              placeholder="ex : 200"
              value={inputValueNum(value.diametre_max_bobine_mm)}
              onChange={(e) =>
                onChange({
                  ...value,
                  diametre_max_bobine_mm: parseNumOrNull(e.target.value),
                })
              }
            />
            <p className="text-xs text-muted-foreground">
              Encombrement maxi du rouleau dans la machine de pose client.
            </p>
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="brief-nb-fronts">Nb fronts en sortie</Label>
          <Input
            id="brief-nb-fronts"
            type="number"
            inputMode="numeric"
            min={1}
            max={12}
            value={inputValueNum(value.nb_fronts_sortie)}
            onChange={(e) => {
              const n = parseNumOrNull(e.target.value);
              onChange({
                ...value,
                nb_fronts_sortie: n === null || n < 1 ? 1 : n,
              });
            }}
            className="sm:max-w-[160px]"
          />
          <p className="text-xs text-muted-foreground">
            Nombre de pistes parallèles en sortie de production. 1 par défaut
            (production en mono-piste).
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
