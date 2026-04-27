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
  PRESTATION_TYPES,
  STATUTS_PARTENAIRE,
  type PartenaireSTCreate,
} from "@/lib/api";

const EMPTY: PartenaireSTCreate = {
  raison_sociale: "",
  siret: null,
  contact_nom: null,
  contact_email: null,
  contact_tel: null,
  prestation_type: null,
  delai_jours_moyen: null,
  qualite_score: null,
  commentaire: null,
  statut: "actif",
};

interface Props {
  initial?: PartenaireSTCreate;
  onSubmit: (data: PartenaireSTCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

const SELECT_CN =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function PartenaireSTForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Partenaire sous-traitance",
}: Props) {
  const [data, setData] = useState<PartenaireSTCreate>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof PartenaireSTCreate>(
    field: K,
    value: PartenaireSTCreate[K]
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
              <Label htmlFor="raison_sociale">Raison sociale *</Label>
              <Input
                id="raison_sociale"
                required
                value={data.raison_sociale}
                onChange={(e) => setField("raison_sociale", e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="siret">SIRET</Label>
              <Input
                id="siret"
                maxLength={14}
                value={data.siret ?? ""}
                onChange={(e) => setField("siret", e.target.value || null)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="contact_nom">Contact</Label>
              <Input
                id="contact_nom"
                value={data.contact_nom ?? ""}
                onChange={(e) =>
                  setField("contact_nom", e.target.value || null)
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="contact_tel">Téléphone</Label>
              <Input
                id="contact_tel"
                value={data.contact_tel ?? ""}
                onChange={(e) =>
                  setField("contact_tel", e.target.value || null)
                }
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="contact_email">Email</Label>
            <Input
              id="contact_email"
              type="email"
              value={data.contact_email ?? ""}
              onChange={(e) =>
                setField("contact_email", e.target.value || null)
              }
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="prestation_type">Type de prestation</Label>
              <select
                id="prestation_type"
                value={data.prestation_type ?? ""}
                onChange={(e) =>
                  setField(
                    "prestation_type",
                    (e.target.value || null) as PartenaireSTCreate["prestation_type"]
                  )
                }
                className={SELECT_CN}
              >
                <option value="">—</option>
                {PRESTATION_TYPES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="delai_jours_moyen">Délai moyen (jours)</Label>
              <Input
                id="delai_jours_moyen"
                type="number"
                min={0}
                value={data.delai_jours_moyen ?? ""}
                onChange={(e) =>
                  setField(
                    "delai_jours_moyen",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="qualite_score">Note qualité (1-5)</Label>
              <Input
                id="qualite_score"
                type="number"
                min={1}
                max={5}
                value={data.qualite_score ?? ""}
                onChange={(e) =>
                  setField(
                    "qualite_score",
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
                setField("statut", e.target.value as PartenaireSTCreate["statut"])
              }
              className={SELECT_CN}
            >
              {STATUTS_PARTENAIRE.map((s) => (
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
