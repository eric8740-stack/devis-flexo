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
  FREQUENCES_ESTIMEES,
  STATUTS_CATALOGUE,
  type CatalogueCreate,
} from "@/lib/api";

const EMPTY: CatalogueCreate = {
  code_produit: "",
  designation: "",
  client_id: 1,
  machine_id: null,
  matiere: null,
  format_mm: null,
  nb_couleurs: null,
  prix_unitaire_eur: null,
  frequence_estimee: null,
  commentaire: null,
  statut: "actif",
};

interface Props {
  initial?: CatalogueCreate;
  onSubmit: (data: CatalogueCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

const SELECT_CN =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function CatalogueForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Produit catalogue",
}: Props) {
  const [data, setData] = useState<CatalogueCreate>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof CatalogueCreate>(
    field: K,
    value: CatalogueCreate[K]
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
              <Label htmlFor="code_produit">Code produit *</Label>
              <Input
                id="code_produit"
                required
                value={data.code_produit}
                onChange={(e) => setField("code_produit", e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="client_id">ID Client (FK) *</Label>
              <Input
                id="client_id"
                type="number"
                required
                min={1}
                value={data.client_id}
                onChange={(e) =>
                  setField("client_id", Number(e.target.value || 1))
                }
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="designation">Désignation *</Label>
            <Input
              id="designation"
              required
              value={data.designation}
              onChange={(e) => setField("designation", e.target.value)}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="machine_id">ID Machine (FK)</Label>
              <Input
                id="machine_id"
                type="number"
                value={data.machine_id ?? ""}
                onChange={(e) =>
                  setField(
                    "machine_id",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="format_mm">Format (mm)</Label>
              <Input
                id="format_mm"
                placeholder="60x80"
                value={data.format_mm ?? ""}
                onChange={(e) =>
                  setField("format_mm", e.target.value || null)
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="nb_couleurs">Nb couleurs</Label>
              <Input
                id="nb_couleurs"
                type="number"
                min={0}
                max={12}
                value={data.nb_couleurs ?? ""}
                onChange={(e) =>
                  setField(
                    "nb_couleurs",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="matiere">Matière</Label>
            <Input
              id="matiere"
              value={data.matiere ?? ""}
              onChange={(e) => setField("matiere", e.target.value || null)}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="prix_unitaire_eur">Prix unitaire (€)</Label>
              <Input
                id="prix_unitaire_eur"
                type="number"
                step="0.0001"
                value={data.prix_unitaire_eur ?? ""}
                onChange={(e) =>
                  setField(
                    "prix_unitaire_eur",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="frequence_estimee">Fréquence</Label>
              <select
                id="frequence_estimee"
                value={data.frequence_estimee ?? ""}
                onChange={(e) =>
                  setField(
                    "frequence_estimee",
                    (e.target.value || null) as CatalogueCreate["frequence_estimee"]
                  )
                }
                className={SELECT_CN}
              >
                <option value="">—</option>
                {FREQUENCES_ESTIMEES.map((f) => (
                  <option key={f} value={f}>
                    {f}
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
                    e.target.value as CatalogueCreate["statut"]
                  )
                }
                className={SELECT_CN}
              >
                {STATUTS_CATALOGUE.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
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
