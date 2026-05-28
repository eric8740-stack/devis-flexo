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
import { SEGMENTS, type ClientCreate } from "@/lib/api";

// Convertit la value d'un <input type="number"> en `number | null`. Une
// chaîne vide est traitée comme "non renseigné" (null) — cohérent avec
// le reste du formulaire qui normalise `value || null` pour les texte.
function parseNumOrNull(v: string): number | null {
  if (v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

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
  // Sprint 16 — profil rebobinage. Booléens à false (server_default
  // backend), 6 autres à null (champs optionnels).
  marquage_bobine_requis: false,
  mandrin_fourni_par_client: false,
  film_protection_requis: false,
  diametre_mandrin_mm: null,
  diametre_max_bobine_mm: null,
  nb_etiq_par_bobine_fixe: null,
  sens_enroulement: null,
  marquage_bobine_format: null,
  conditionnement_souhaite: null,
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

        </CardContent>
      </Card>

      {/* ────────────────────────────────────────────────────────── */}
      {/* Sprint 16 — Profil rebobinage client                        */}
      {/* ────────────────────────────────────────────────────────── */}
      <Card className="mt-6" data-testid="client-rebobinage-section">
        <CardHeader>
          <CardTitle>Rebobinage</CardTitle>
          <CardDescription>
            Exigences et spécifications du client pour le rebobinage des
            bobines livrées. Ces champs auto-remplissent l&apos;étape
            rebobinage des devis créés pour ce client.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          {/* 3 booléens : exigences client */}
          <fieldset className="grid gap-3 sm:grid-cols-3">
            <label className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 text-sm">
              <input
                id="marquage_bobine_requis"
                type="checkbox"
                checked={data.marquage_bobine_requis}
                onChange={(e) =>
                  setField("marquage_bobine_requis", e.target.checked)
                }
                className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
              />
              <span>Marquage bobine requis</span>
            </label>
            <label className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 text-sm">
              <input
                id="mandrin_fourni_par_client"
                type="checkbox"
                checked={data.mandrin_fourni_par_client}
                onChange={(e) =>
                  setField("mandrin_fourni_par_client", e.target.checked)
                }
                className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
              />
              <span>Mandrin fourni par le client</span>
            </label>
            <label className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 text-sm">
              <input
                id="film_protection_requis"
                type="checkbox"
                checked={data.film_protection_requis}
                onChange={(e) =>
                  setField("film_protection_requis", e.target.checked)
                }
                className="mt-0.5 h-4 w-4 cursor-pointer accent-foreground"
              />
              <span>Film protection requis</span>
            </label>
          </fieldset>

          {/* 4 numériques : spécifications bobine */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="diametre_mandrin_mm">
                Ø Mandrin bobine (mm)
              </Label>
              <Input
                id="diametre_mandrin_mm"
                type="number"
                min={1}
                step={1}
                value={data.diametre_mandrin_mm ?? ""}
                onChange={(e) =>
                  setField("diametre_mandrin_mm", parseNumOrNull(e.target.value))
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="diametre_max_bobine_mm">
                Ø Max bobine livrée (mm)
              </Label>
              <Input
                id="diametre_max_bobine_mm"
                type="number"
                min={1}
                step={1}
                value={data.diametre_max_bobine_mm ?? ""}
                onChange={(e) =>
                  setField(
                    "diametre_max_bobine_mm",
                    parseNumOrNull(e.target.value),
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="nb_etiq_par_bobine_fixe">
                Nb étiquettes / bobine (fixe)
              </Label>
              <Input
                id="nb_etiq_par_bobine_fixe"
                type="number"
                min={1}
                step={1}
                value={data.nb_etiq_par_bobine_fixe ?? ""}
                onChange={(e) =>
                  setField(
                    "nb_etiq_par_bobine_fixe",
                    parseNumOrNull(e.target.value),
                  )
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="sens_enroulement">
                Sens d&apos;enroulement (0..9)
              </Label>
              <Input
                id="sens_enroulement"
                type="number"
                min={0}
                max={9}
                step={1}
                value={data.sens_enroulement ?? ""}
                onChange={(e) =>
                  setField("sens_enroulement", parseNumOrNull(e.target.value))
                }
              />
              <p className="text-xs text-muted-foreground">
                Convention SE0-SE9 (stockage brut). SE1-SE8 = sens imprimés ;
                SE0/SE9 = bobines livrées vierges, sans impression. La
                validation 0..9 est appliquée côté serveur.
              </p>
            </div>
          </div>

          {/* 2 textes : détails */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="marquage_bobine_format">
                Format du marquage
              </Label>
              <Input
                id="marquage_bobine_format"
                value={data.marquage_bobine_format ?? ""}
                onChange={(e) =>
                  setField(
                    "marquage_bobine_format",
                    e.target.value || null,
                  )
                }
                placeholder="Ex : étiquette identification A6"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="conditionnement_souhaite">
                Conditionnement souhaité
              </Label>
              <Input
                id="conditionnement_souhaite"
                value={data.conditionnement_souhaite ?? ""}
                onChange={(e) =>
                  setField(
                    "conditionnement_souhaite",
                    e.target.value || null,
                  )
                }
                placeholder="Ex : carton renforcé export"
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
