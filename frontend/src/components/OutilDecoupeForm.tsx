"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type OutilDecoupeCreate } from "@/lib/api";

const EMPTY: OutilDecoupeCreate = {
  libelle: "",
  format_l_mm: 60,
  format_h_mm: 40,
  nb_poses_l: 1,
  nb_poses_h: 1,
  forme_speciale: false,
  actif: true,
};

interface Props {
  initial?: OutilDecoupeCreate;
  onSubmit: (data: OutilDecoupeCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

export function OutilDecoupeForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Outil de découpe",
}: Props) {
  const [data, setData] = useState<OutilDecoupeCreate>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof OutilDecoupeCreate>(
    field: K,
    value: OutilDecoupeCreate[K]
  ) => setData((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await onSubmit(data);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid gap-2">
            <Label htmlFor="libelle">Libellé *</Label>
            <Input
              id="libelle"
              required
              value={data.libelle}
              onChange={(e) => setField("libelle", e.target.value)}
              placeholder="ex. outil_60x40_3p1d"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="format_l_mm">Largeur étiquette (mm) *</Label>
              <Input
                id="format_l_mm"
                type="number"
                min={1}
                required
                value={data.format_l_mm}
                onChange={(e) =>
                  setField("format_l_mm", Number(e.target.value || 0))
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="format_h_mm">Hauteur étiquette (mm) *</Label>
              <Input
                id="format_h_mm"
                type="number"
                min={1}
                required
                value={data.format_h_mm}
                onChange={(e) =>
                  setField("format_h_mm", Number(e.target.value || 0))
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="nb_poses_l">Nb poses largeur *</Label>
              <Input
                id="nb_poses_l"
                type="number"
                min={1}
                required
                value={data.nb_poses_l}
                onChange={(e) =>
                  setField("nb_poses_l", Number(e.target.value || 1))
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="nb_poses_h">Nb poses développement *</Label>
              <Input
                id="nb_poses_h"
                type="number"
                min={1}
                required
                value={data.nb_poses_h}
                onChange={(e) =>
                  setField("nb_poses_h", Number(e.target.value || 1))
                }
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="forme_speciale"
              type="checkbox"
              checked={data.forme_speciale}
              onChange={(e) => setField("forme_speciale", e.target.checked)}
              className="h-4 w-4"
            />
            <Label htmlFor="forme_speciale" className="cursor-pointer">
              Forme spéciale (surcoût plaque +40 % si nouvel outil)
            </Label>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="actif"
              type="checkbox"
              checked={data.actif}
              onChange={(e) => setField("actif", e.target.checked)}
              className="h-4 w-4"
            />
            <Label htmlFor="actif" className="cursor-pointer">
              Actif (proposé dans les nouveaux devis)
            </Label>
          </div>

          <div className="flex justify-end gap-2">
            {onCancel && (
              <Button type="button" variant="ghost" onClick={onCancel}>
                Annuler
              </Button>
            )}
            <Button type="submit" disabled={busy}>
              {busy ? "Enregistrement…" : submitLabel}
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}
