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
import { SEGMENTS, type ClientCreate } from "@/lib/api";

const EMPTY_CLIENT: ClientCreate = {
  raison_sociale: "",
  siret: null,
  adresse_fact: null,
  cp_fact: null,
  ville_fact: null,
  contact: null,
  email: null,
  tel: null,
  segment: null,
  date_creation: null,
};

interface ClientFormProps {
  initial?: ClientCreate;
  onSubmit: (data: ClientCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

export function ClientForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Client",
}: ClientFormProps) {
  const [data, setData] = useState<ClientCreate>(initial ?? EMPTY_CLIENT);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setField = <K extends keyof ClientCreate>(
    field: K,
    value: ClientCreate[K]
  ) => setData((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(data);
    } finally {
      setIsSubmitting(false);
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
            <Label htmlFor="raison_sociale">Raison sociale *</Label>
            <Input
              id="raison_sociale"
              required
              value={data.raison_sociale}
              onChange={(e) => setField("raison_sociale", e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="siret">SIRET</Label>
              <Input
                id="siret"
                maxLength={14}
                value={data.siret ?? ""}
                onChange={(e) => setField("siret", e.target.value || null)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="segment">Segment</Label>
              <select
                id="segment"
                value={data.segment ?? ""}
                onChange={(e) => setField("segment", e.target.value || null)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="">—</option>
                {SEGMENTS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="adresse_fact">Adresse facturation</Label>
            <Input
              id="adresse_fact"
              value={data.adresse_fact ?? ""}
              onChange={(e) =>
                setField("adresse_fact", e.target.value || null)
              }
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="cp_fact">Code postal</Label>
              <Input
                id="cp_fact"
                value={data.cp_fact ?? ""}
                onChange={(e) => setField("cp_fact", e.target.value || null)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ville_fact">Ville</Label>
              <Input
                id="ville_fact"
                value={data.ville_fact ?? ""}
                onChange={(e) =>
                  setField("ville_fact", e.target.value || null)
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="contact">Contact</Label>
              <Input
                id="contact"
                value={data.contact ?? ""}
                onChange={(e) => setField("contact", e.target.value || null)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tel">Téléphone</Label>
              <Input
                id="tel"
                value={data.tel ?? ""}
                onChange={(e) => setField("tel", e.target.value || null)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={data.email ?? ""}
                onChange={(e) => setField("email", e.target.value || null)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="date_creation">Date de création</Label>
              <Input
                id="date_creation"
                type="date"
                value={data.date_creation ?? ""}
                onChange={(e) =>
                  setField("date_creation", e.target.value || null)
                }
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            {onCancel && (
              <Button type="button" variant="ghost" onClick={onCancel}>
                Annuler
              </Button>
            )}
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Enregistrement…" : submitLabel}
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}
