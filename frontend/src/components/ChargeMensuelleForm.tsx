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
import {
  CATEGORIES_CHARGE,
  type ChargeMensuelleCreate,
} from "@/lib/api";

const today = () => new Date().toISOString().slice(0, 10);

const EMPTY: ChargeMensuelleCreate = {
  libelle: "",
  categorie: "loyer",
  montant_eur: 0,
  date_debut: today(),
  date_fin: null,
  commentaire: null,
};

interface Props {
  initial?: ChargeMensuelleCreate;
  onSubmit: (data: ChargeMensuelleCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

const SELECT_CN =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function ChargeMensuelleForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Charge mensuelle",
}: Props) {
  const [data, setData] = useState<ChargeMensuelleCreate>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof ChargeMensuelleCreate>(
    field: K,
    value: ChargeMensuelleCreate[K]
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
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="categorie">Catégorie *</Label>
              <select
                id="categorie"
                value={data.categorie}
                onChange={(e) =>
                  setField(
                    "categorie",
                    e.target.value as ChargeMensuelleCreate["categorie"]
                  )
                }
                className={SELECT_CN}
              >
                {CATEGORIES_CHARGE.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="montant_eur">Montant mensuel (€) *</Label>
              <Input
                id="montant_eur"
                type="number"
                step="0.01"
                required
                min={0}
                value={data.montant_eur}
                onChange={(e) =>
                  setField("montant_eur", Number(e.target.value || 0))
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="date_debut">Date début *</Label>
              <Input
                id="date_debut"
                type="date"
                required
                value={data.date_debut}
                onChange={(e) => setField("date_debut", e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_fin">Date fin (vide = en cours)</Label>
              <Input
                id="date_fin"
                type="date"
                value={data.date_fin ?? ""}
                onChange={(e) =>
                  setField("date_fin", e.target.value || null)
                }
              />
            </div>
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
