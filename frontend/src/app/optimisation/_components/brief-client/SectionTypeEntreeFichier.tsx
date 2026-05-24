"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { type BriefClientData, type TypeEntreeFichier } from "./types";

interface Props {
  value: BriefClientData;
  onChange: (next: BriefClientData) => void;
}

const OPTIONS: {
  value: TypeEntreeFichier;
  titre: string;
  aide: string;
}[] = [
  {
    value: "vierge",
    titre: "Rouleau vierge",
    aide: "Étiquettes blanches non imprimées (étiquettes neutres prêtes à imprimer chez le client).",
  },
  {
    value: "bat_pro_fourni",
    titre: "BAT / PDF fourni par le client",
    aide: "Le client fournit un fichier prêt à imprimer (PDF haute définition, BAT validé).",
  },
  {
    value: "a_designer",
    titre: "À concevoir",
    aide: "Création graphique à faire par l'imprimerie (devis avec poste design).",
  },
];

export function SectionTypeEntreeFichier({ value, onChange }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Type d&apos;entrée fichier</CardTitle>
        <CardDescription>
          Ce que le client fournit à l&apos;imprimerie pour démarrer la
          production. Détermine si un poste design doit être ajouté au devis.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {OPTIONS.map((opt) => {
          const checked = value.type_entree_fichier === opt.value;
          return (
            <label
              key={opt.value}
              className={`flex min-h-[44px] cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors ${
                checked
                  ? "border-foreground bg-accent"
                  : "border-border bg-background hover:bg-accent/40"
              }`}
            >
              <input
                type="radio"
                name="brief-type-entree"
                value={opt.value}
                checked={checked}
                onChange={() =>
                  onChange({ ...value, type_entree_fichier: opt.value })
                }
                className="mt-1 h-4 w-4 accent-foreground"
              />
              <div className="flex-1">
                <div className="text-sm font-medium">{opt.titre}</div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {opt.aide}
                </p>
              </div>
            </label>
          );
        })}
      </CardContent>
    </Card>
  );
}
