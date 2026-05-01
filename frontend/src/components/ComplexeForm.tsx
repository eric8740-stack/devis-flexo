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
import { FAMILLES_COMPLEXE, type ComplexeCreate } from "@/lib/api";

const EMPTY: ComplexeCreate = {
  reference: "",
  famille: "papier_couche",
  face_matiere: null,
  grammage_g_m2: null,
  adhesif_type: null,
  prix_m2_eur: 0,
  fournisseur_id: null,
  actif: true,
  commentaire: null,
};

interface Props {
  initial?: ComplexeCreate;
  onSubmit: (data: ComplexeCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

const SELECT_CN =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function ComplexeForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Complexe adhésif",
}: Props) {
  const [data, setData] = useState<ComplexeCreate>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof ComplexeCreate>(
    field: K,
    value: ComplexeCreate[K]
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
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="reference">Référence *</Label>
              <Input
                id="reference"
                required
                value={data.reference}
                onChange={(e) => setField("reference", e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="famille">Famille *</Label>
              <select
                id="famille"
                value={data.famille}
                onChange={(e) =>
                  setField(
                    "famille",
                    e.target.value as ComplexeCreate["famille"]
                  )
                }
                className={SELECT_CN}
              >
                {FAMILLES_COMPLEXE.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="face_matiere">Face / matière</Label>
            <Input
              id="face_matiere"
              value={data.face_matiere ?? ""}
              onChange={(e) =>
                setField("face_matiere", e.target.value || null)
              }
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="grammage_g_m2">Grammage (g/m²)</Label>
              <Input
                id="grammage_g_m2"
                type="number"
                min={1}
                value={data.grammage_g_m2 ?? ""}
                onChange={(e) =>
                  setField(
                    "grammage_g_m2",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="adhesif_type">Type d&apos;adhésif</Label>
              <Input
                id="adhesif_type"
                value={data.adhesif_type ?? ""}
                onChange={(e) =>
                  setField("adhesif_type", e.target.value || null)
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="prix_m2_eur">Prix au m² (€) *</Label>
              <Input
                id="prix_m2_eur"
                type="number"
                step="0.0001"
                required
                min={0.0001}
                value={data.prix_m2_eur}
                onChange={(e) =>
                  setField("prix_m2_eur", Number(e.target.value || 0))
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="fournisseur_id">ID Fournisseur (FK)</Label>
              <Input
                id="fournisseur_id"
                type="number"
                value={data.fournisseur_id ?? ""}
                onChange={(e) =>
                  setField(
                    "fournisseur_id",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
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
              Actif (proposé dans la sélection des nouveaux devis)
            </Label>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="commentaire">Commentaire</Label>
            <Input
              id="commentaire"
              value={data.commentaire ?? ""}
              onChange={(e) =>
                setField("commentaire", e.target.value || null)
              }
            />
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
