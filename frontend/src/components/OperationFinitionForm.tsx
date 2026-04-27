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
  STATUTS_OPERATION,
  UNITES_FACTURATION,
  type OperationFinitionCreate,
} from "@/lib/api";

const EMPTY: OperationFinitionCreate = {
  nom: "",
  unite_facturation: "m2",
  cout_unitaire_eur: null,
  temps_minutes_unite: null,
  statut: "actif",
  commentaire: null,
};

interface Props {
  initial?: OperationFinitionCreate;
  onSubmit: (data: OperationFinitionCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

const SELECT_CN =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function OperationFinitionForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Opération de finition",
}: Props) {
  const [data, setData] = useState<OperationFinitionCreate>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof OperationFinitionCreate>(
    field: K,
    value: OperationFinitionCreate[K]
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
            <Label htmlFor="nom">Nom *</Label>
            <Input
              id="nom"
              required
              value={data.nom}
              onChange={(e) => setField("nom", e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="unite_facturation">Unité de facturation *</Label>
              <select
                id="unite_facturation"
                value={data.unite_facturation}
                onChange={(e) =>
                  setField(
                    "unite_facturation",
                    e.target.value as OperationFinitionCreate["unite_facturation"]
                  )
                }
                className={SELECT_CN}
              >
                {UNITES_FACTURATION.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="statut">Statut</Label>
              <select
                id="statut"
                value={data.statut}
                onChange={(e) =>
                  setField(
                    "statut",
                    e.target.value as OperationFinitionCreate["statut"]
                  )
                }
                className={SELECT_CN}
              >
                {STATUTS_OPERATION.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="cout_unitaire_eur">Coût unitaire (€)</Label>
              <Input
                id="cout_unitaire_eur"
                type="number"
                step="0.0001"
                value={data.cout_unitaire_eur ?? ""}
                onChange={(e) =>
                  setField(
                    "cout_unitaire_eur",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="temps_minutes_unite">Temps machine (min/unité)</Label>
              <Input
                id="temps_minutes_unite"
                type="number"
                step="0.01"
                value={data.temps_minutes_unite ?? ""}
                onChange={(e) =>
                  setField(
                    "temps_minutes_unite",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
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
