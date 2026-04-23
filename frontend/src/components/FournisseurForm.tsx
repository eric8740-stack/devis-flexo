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
  CATEGORIES_FOURNISSEUR,
  type FournisseurCreate,
} from "@/lib/api";

const EMPTY_FOURNISSEUR: FournisseurCreate = {
  raison_sociale: "",
  categorie: null,
  contact: null,
  email: null,
  tel: null,
  conditions_paiement: null,
  delai_livraison_j: null,
};

interface FournisseurFormProps {
  initial?: FournisseurCreate;
  onSubmit: (data: FournisseurCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

export function FournisseurForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Fournisseur",
}: FournisseurFormProps) {
  const [data, setData] = useState<FournisseurCreate>(
    initial ?? EMPTY_FOURNISSEUR
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setField = <K extends keyof FournisseurCreate>(
    field: K,
    value: FournisseurCreate[K]
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

          <div className="grid gap-2">
            <Label htmlFor="categorie">Catégorie</Label>
            <select
              id="categorie"
              value={data.categorie ?? ""}
              onChange={(e) => setField("categorie", e.target.value || null)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="">—</option>
              {CATEGORIES_FOURNISSEUR.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
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

          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={data.email ?? ""}
              onChange={(e) => setField("email", e.target.value || null)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="conditions_paiement">
                Conditions de paiement
              </Label>
              <Input
                id="conditions_paiement"
                value={data.conditions_paiement ?? ""}
                onChange={(e) =>
                  setField("conditions_paiement", e.target.value || null)
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="delai_livraison_j">
                Délai de livraison (jours)
              </Label>
              <Input
                id="delai_livraison_j"
                type="number"
                value={data.delai_livraison_j ?? ""}
                onChange={(e) =>
                  setField(
                    "delai_livraison_j",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
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
