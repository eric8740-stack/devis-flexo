"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { updateEntreprise, type Entreprise } from "@/lib/api";

interface EntrepriseFormProps {
  initial: Entreprise;
}

export function EntrepriseForm({ initial }: EntrepriseFormProps) {
  const [data, setData] = useState<Entreprise>(initial);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const setField = <K extends keyof Entreprise>(
    field: K,
    value: Entreprise[K]
  ) => setData((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const { id: _id, ...payload } = data;
      void _id;
      const updated = await updateEntreprise(payload);
      setData(updated);
      toast({
        title: "Paramètres enregistrés",
        description: "Les paramètres entreprise ont été mis à jour.",
      });
    } catch (error) {
      toast({
        title: "Erreur",
        description:
          error instanceof Error ? error.message : "Erreur inconnue",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Card>
        <CardHeader>
          <CardTitle>Paramètres entreprise</CardTitle>
          <CardDescription>
            Données émetteur utilisées dans les devis et le moteur de calcul.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid gap-2">
            <Label htmlFor="raison_sociale">Raison sociale *</Label>
            <Input
              id="raison_sociale"
              value={data.raison_sociale}
              onChange={(e) => setField("raison_sociale", e.target.value)}
              required
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="siret">SIRET</Label>
            <Input
              id="siret"
              value={data.siret}
              onChange={(e) => setField("siret", e.target.value)}
              maxLength={14}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="adresse">Adresse</Label>
            <Input
              id="adresse"
              value={data.adresse ?? ""}
              onChange={(e) => setField("adresse", e.target.value || null)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="cp">Code postal</Label>
              <Input
                id="cp"
                value={data.cp ?? ""}
                onChange={(e) => setField("cp", e.target.value || null)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ville">Ville</Label>
              <Input
                id="ville"
                value={data.ville ?? ""}
                onChange={(e) => setField("ville", e.target.value || null)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="tel">Téléphone</Label>
              <Input
                id="tel"
                value={data.tel ?? ""}
                onChange={(e) => setField("tel", e.target.value || null)}
              />
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
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="pct_fg">Frais généraux (ratio, ex. 0.08)</Label>
              <Input
                id="pct_fg"
                type="number"
                step="0.01"
                value={data.pct_fg ?? ""}
                onChange={(e) =>
                  setField(
                    "pct_fg",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="pct_marge_defaut">
                Marge par défaut (ratio, ex. 0.22)
              </Label>
              <Input
                id="pct_marge_defaut"
                type="number"
                step="0.01"
                value={data.pct_marge_defaut ?? ""}
                onChange={(e) =>
                  setField(
                    "pct_marge_defaut",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="heures_prod_presse_mois">
                Heures productives presse / mois
              </Label>
              <Input
                id="heures_prod_presse_mois"
                type="number"
                value={data.heures_prod_presse_mois ?? ""}
                onChange={(e) =>
                  setField(
                    "heures_prod_presse_mois",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="heures_prod_finition_mois">
                Heures productives finition / mois
              </Label>
              <Input
                id="heures_prod_finition_mois"
                type="number"
                value={data.heures_prod_finition_mois ?? ""}
                onChange={(e) =>
                  setField(
                    "heures_prod_finition_mois",
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
              />
            </div>
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Enregistrement…" : "Enregistrer"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  );
}
