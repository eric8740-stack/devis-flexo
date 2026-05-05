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
import { type MachineCreate } from "@/lib/api";

// Mini-fix vitesse-machine 05/05/2026 :
// - On expose 3 champs jusque-là invisibles : laize_max_mm (NOT NULL BDD),
//   vitesse_moyenne_m_h (pilote P5+P7), duree_calage_h (pilote P7).
// - Vocabulaire UI = m/min (standard flexo). Stockage BDD = m/h. Conversion
//   ×60 transparente au submit, /60 à l'init pour l'édition.
// - Le champ legacy `largeur_max_mm` (Integer NULL) sort de l'UI pour ne pas
//   créer de confusion avec la nouvelle « Laize max ». Il reste dans le type
//   et est préservé tel quel à l'édition (on ne l'envoie pas dans le payload
//   donc le PATCH partiel garde la valeur existante en BDD).

const DEFAULT_LAIZE_MAX_MM = 330;
const DEFAULT_DUREE_CALAGE_H = 1.0;

const EMPTY: MachineCreate = {
  nom: "",
  largeur_max_mm: null,
  laize_max_mm: DEFAULT_LAIZE_MAX_MM,
  vitesse_max_m_min: null,
  vitesse_moyenne_m_h: null,
  duree_calage_h: DEFAULT_DUREE_CALAGE_H,
  nb_couleurs: null,
  cout_horaire_eur: null,
  actif: true,
  commentaire: null,
};

interface Props {
  initial?: MachineCreate;
  onSubmit: (data: MachineCreate) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
  title?: string;
}

export function MachineForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Enregistrer",
  title = "Machine",
}: Props) {
  const [data, setData] = useState<MachineCreate>(initial ?? EMPTY);
  // State local en m/min (vocabulaire flexo). Init depuis le m/h BDD à
  // l'édition. Si la valeur stockée n'est pas un multiple exact de 60,
  // on arrondit pour l'affichage — le re-submit ré-écrit la valeur ronde.
  const [vitesseMoyenneMmin, setVitesseMoyenneMmin] = useState<number | null>(
    initial?.vitesse_moyenne_m_h != null
      ? Math.round(initial.vitesse_moyenne_m_h / 60)
      : null
  );
  const [busy, setBusy] = useState(false);

  const setField = <K extends keyof MachineCreate>(
    field: K,
    value: MachineCreate[K]
  ) => setData((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await onSubmit({
        ...data,
        // Conversion m/min → m/h au moment du submit. null si vide
        // (mais le champ est required HTML, donc en pratique non null).
        vitesse_moyenne_m_h:
          vitesseMoyenneMmin != null ? vitesseMoyenneMmin * 60 : null,
      });
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
          {/* 1. Nom */}
          <div className="grid gap-2">
            <Label htmlFor="nom">Nom *</Label>
            <Input
              id="nom"
              required
              value={data.nom}
              onChange={(e) => setField("nom", e.target.value)}
            />
          </div>

          {/* 2. Laize max (mm) — required, NOT NULL en BDD */}
          <div className="grid gap-2">
            <Label htmlFor="laize_max_mm">Laize max (mm) *</Label>
            <Input
              id="laize_max_mm"
              type="number"
              step="0.01"
              min={1}
              required
              value={data.laize_max_mm ?? ""}
              onChange={(e) =>
                setField(
                  "laize_max_mm",
                  e.target.value === ""
                    ? DEFAULT_LAIZE_MAX_MM
                    : Number(e.target.value)
                )
              }
            />
            <p className="text-xs text-muted-foreground">
              Laize physique maximale de la presse (largeur de bande
              qu&apos;elle accepte). Ex&nbsp;: Mark Andy P5 = 330&nbsp;mm.
            </p>
          </div>

          {/* 3. Vitesse catalogue (m/min, indicative) — facultatif, pas utilisé par le moteur */}
          <div className="grid gap-2">
            <Label htmlFor="vitesse_max_m_min">
              Vitesse catalogue (m/min, indicative)
            </Label>
            <Input
              id="vitesse_max_m_min"
              type="number"
              min={1}
              value={data.vitesse_max_m_min ?? ""}
              onChange={(e) =>
                setField(
                  "vitesse_max_m_min",
                  e.target.value === "" ? null : Number(e.target.value)
                )
              }
            />
            <p className="text-xs text-muted-foreground">
              Donnée du constructeur, à titre indicatif. N&apos;impacte pas
              le calcul du devis — c&apos;est le champ <em>Vitesse moyenne
              réaliste</em> juste en-dessous qui pilote P5 et P7.
            </p>
          </div>

          {/* 4. Vitesse moyenne réaliste (m/min) — required, pilote P5+P7 */}
          <div className="grid gap-2">
            <Label htmlFor="vitesse_moyenne_m_min">
              Vitesse moyenne réaliste (m/min) *
            </Label>
            <Input
              id="vitesse_moyenne_m_min"
              type="number"
              min={1}
              max={999}
              required
              placeholder="ex: 100"
              value={vitesseMoyenneMmin ?? ""}
              onChange={(e) =>
                setVitesseMoyenneMmin(
                  e.target.value === "" ? null : Number(e.target.value)
                )
              }
            />
            <p className="text-xs text-muted-foreground">
              La vitesse réelle que tu tiens en production sur un job complet
              (avec arrêts, changements bobine, séchage). C&apos;est elle
              qui pilote le calcul P5 (Roulage) et P7 (MO opérateur).
              Ordre de grandeur flexo : 70-100 m/min, pas la 250-300 catalogue.
            </p>
          </div>

          {/* 5. Durée calage (h) — required, pilote P7 calage */}
          <div className="grid gap-2">
            <Label htmlFor="duree_calage_h">Durée calage (h) *</Label>
            <Input
              id="duree_calage_h"
              type="number"
              step="0.01"
              min={0.01}
              max={99.99}
              required
              value={data.duree_calage_h ?? ""}
              onChange={(e) =>
                setField(
                  "duree_calage_h",
                  e.target.value === "" ? null : Number(e.target.value)
                )
              }
            />
            <p className="text-xs text-muted-foreground">
              Durée typique de mise en route + calage avant production.
              Format décimal&nbsp;: <em>1.00</em>=1h, <em>0.50</em>=30 min,
              <em> 1.50</em>=1h30. Sert au calcul P7 MO opérateur.
            </p>
          </div>

          {/* 6 + 7. Nb couleurs et coût horaire en grille */}
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

          {/* 8. Actif */}
          <div className="flex items-center gap-2">
            <input
              id="actif"
              type="checkbox"
              checked={data.actif}
              onChange={(e) => setField("actif", e.target.checked)}
              className="h-4 w-4"
            />
            <Label htmlFor="actif" className="cursor-pointer">
              Actif (apparaît dans la sélection des nouveaux devis)
            </Label>
          </div>

          {/* 9. Commentaire */}
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
