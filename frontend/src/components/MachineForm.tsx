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
import { STATUTS_MACHINE, type MachineCreate } from "@/lib/api";

const EMPTY: MachineCreate = {
  nom: "",
  largeur_max_mm: null,
  vitesse_max_m_min: null,
  nb_couleurs: null,
  cout_horaire_eur: null,
  statut: "actif",
  commentaire: null,
};

interface Props {
  initial?: MachineCreate;
  onSubmit: (data: MachineCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

const SELECT_CN =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function MachineForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Machine",
}: Props) {
  const [data, setData] = useState<MachineCreate>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof MachineCreate>(
    field: K,
    value: MachineCreate[K]
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
              <Label htmlFor="largeur_max_mm">Laize max (mm)</Label>
              <Input
                id="largeur_max_mm"
                type="number"
                value={data.largeur_max_mm ?? ""}
                onChange={(e) =>
                  setField(
                    "largeur_max_mm",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="vitesse_max_m_min">Vitesse max (m/min)</Label>
              <Input
                id="vitesse_max_m_min"
                type="number"
                value={data.vitesse_max_m_min ?? ""}
                onChange={(e) =>
                  setField(
                    "vitesse_max_m_min",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="nb_couleurs">Nb couleurs</Label>
              <Input
                id="nb_couleurs"
                type="number"
                min={1}
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
            <div className="grid gap-2">
              <Label htmlFor="cout_horaire_eur">Coût horaire (€)</Label>
              <Input
                id="cout_horaire_eur"
                type="number"
                step="0.01"
                value={data.cout_horaire_eur ?? ""}
                onChange={(e) =>
                  setField(
                    "cout_horaire_eur",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="statut">Statut</Label>
            <select
              id="statut"
              value={data.statut}
              onChange={(e) =>
                setField("statut", e.target.value as MachineCreate["statut"])
              }
              className={SELECT_CN}
            >
              {STATUTS_MACHINE.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
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
