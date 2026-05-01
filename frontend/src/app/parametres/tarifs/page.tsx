"use client";

import { useCallback, useEffect, useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import {
  getTarifsGrouped,
  resetPoste,
  type TarifPosteByPoste,
  type TarifPosteRead,
  updateTarifValeur,
} from "@/lib/api";

interface PosteSectionProps {
  poste: TarifPosteByPoste;
  onValueChange: (cle: string, value: string) => void;
  onSavePoste: (numero: number) => Promise<void>;
  onResetPoste: (numero: number) => Promise<void>;
  editedValues: Record<string, string>;
  isSaving: boolean;
  isResetting: boolean;
}

function PosteSection({
  poste,
  onValueChange,
  onSavePoste,
  onResetPoste,
  editedValues,
  isSaving,
  isResetting,
}: PosteSectionProps) {
  const hasDirty = poste.parametres.some(
    (p) => editedValues[p.cle] !== undefined && editedValues[p.cle] !== p.valeur_defaut
  );
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Poste {poste.poste_numero} — {poste.libelle_poste}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6">
        {poste.parametres.map((p) => (
          <ParametreInput
            key={p.cle}
            param={p}
            value={editedValues[p.cle] ?? p.valeur_defaut}
            onChange={(v) => onValueChange(p.cle, v)}
          />
        ))}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={!hasDirty || isSaving}
            onClick={() => onSavePoste(poste.poste_numero)}
          >
            {isSaving
              ? "Enregistrement…"
              : `Sauvegarder Poste ${poste.poste_numero}`}
          </Button>
          <ResetPosteAlert
            posteNumero={poste.poste_numero}
            posteLibelle={poste.libelle_poste}
            disabled={isResetting}
            onConfirm={() => onResetPoste(poste.poste_numero)}
          />
        </div>
      </CardContent>
    </Card>
  );
}

interface ParametreInputProps {
  param: TarifPosteRead;
  value: string;
  onChange: (value: string) => void;
}

function ParametreInput({ param, value, onChange }: ParametreInputProps) {
  const min = param.valeur_min !== null ? Number(param.valeur_min) : undefined;
  const max = param.valeur_max !== null ? Number(param.valeur_max) : undefined;
  const numericValue = Number(value);
  const outOfBounds =
    !Number.isNaN(numericValue) &&
    ((min !== undefined && numericValue < min) ||
      (max !== undefined && numericValue > max));
  return (
    <div className="grid gap-2">
      <Label htmlFor={`tarif-${param.cle}`}>
        {param.libelle}{" "}
        <span className="text-xs font-normal text-muted-foreground">
          ({param.unite})
        </span>
      </Label>
      <div className="flex items-center gap-2">
        <Input
          id={`tarif-${param.cle}`}
          type="number"
          step="0.01"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="max-w-xs"
        />
        {param.valeur_min && param.valeur_max ? (
          <span className="text-xs text-muted-foreground">
            min {param.valeur_min} · max {param.valeur_max}
          </span>
        ) : null}
      </div>
      {outOfBounds ? (
        <p className="text-xs text-red-600">
          Valeur hors plage [{param.valeur_min} – {param.valeur_max}]
        </p>
      ) : null}
      {param.description ? (
        <p className="text-xs text-muted-foreground">{param.description}</p>
      ) : null}
    </div>
  );
}

interface ResetPosteAlertProps {
  posteNumero: number;
  posteLibelle: string;
  disabled: boolean;
  onConfirm: () => Promise<void>;
}

function ResetPosteAlert({
  posteNumero,
  posteLibelle,
  disabled,
  onConfirm,
}: ResetPosteAlertProps) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button type="button" variant="outline" disabled={disabled}>
          Réinitialiser Poste {posteNumero}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            Réinitialiser les paramètres du Poste {posteNumero}&nbsp;?
          </AlertDialogTitle>
          <AlertDialogDescription>
            Toutes les valeurs du poste « {posteLibelle} » seront restaurées
            aux valeurs initiales (seed). Cette action est irréversible mais
            n&apos;affecte pas les devis déjà sauvegardés.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Annuler</AlertDialogCancel>
          <AlertDialogAction onClick={() => void onConfirm()}>
            Réinitialiser
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default function ParametresTarifsPage() {
  const [grouped, setGrouped] = useState<TarifPosteByPoste[] | null>(null);
  const [editedValues, setEditedValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [savingPoste, setSavingPoste] = useState<number | null>(null);
  const [resettingPoste, setResettingPoste] = useState<number | null>(null);
  const { toast } = useToast();

  const loadTarifs = useCallback(async () => {
    try {
      const data = await getTarifsGrouped();
      setGrouped(data.postes);
      setEditedValues({});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void loadTarifs();
  }, [loadTarifs]);

  const handleValueChange = useCallback((cle: string, value: string) => {
    setEditedValues((prev) => ({ ...prev, [cle]: value }));
  }, []);

  const handleSavePoste = useCallback(
    async (posteNumero: number) => {
      if (!grouped) return;
      const poste = grouped.find((p) => p.poste_numero === posteNumero);
      if (!poste) return;
      const dirtyParams = poste.parametres.filter(
        (p) =>
          editedValues[p.cle] !== undefined &&
          editedValues[p.cle] !== p.valeur_defaut
      );
      if (dirtyParams.length === 0) return;
      setSavingPoste(posteNumero);
      try {
        for (const p of dirtyParams) {
          await updateTarifValeur(p.cle, editedValues[p.cle]);
        }
        toast({
          title: "Tarifs enregistrés",
          description: `${dirtyParams.length} paramètre(s) du Poste ${posteNumero} mis à jour.`,
        });
        await loadTarifs();
      } catch (e) {
        toast({
          title: "Erreur",
          description: e instanceof Error ? e.message : String(e),
          variant: "destructive",
        });
      } finally {
        setSavingPoste(null);
      }
    },
    [grouped, editedValues, loadTarifs, toast]
  );

  const handleResetPoste = useCallback(
    async (posteNumero: number) => {
      setResettingPoste(posteNumero);
      try {
        const r = await resetPoste(posteNumero);
        toast({
          title: "Poste réinitialisé",
          description: `${r.n_reset} paramètre(s) du Poste ${posteNumero} restauré(s).`,
        });
        await loadTarifs();
      } catch (e) {
        toast({
          title: "Erreur",
          description: e instanceof Error ? e.message : String(e),
          variant: "destructive",
        });
      } finally {
        setResettingPoste(null);
      }
    },
    [loadTarifs, toast]
  );

  if (error) {
    return <p className="text-sm text-red-600">Erreur de chargement : {error}</p>;
  }
  if (!grouped) {
    return <p className="text-sm text-muted-foreground">Chargement…</p>;
  }
  return (
    <div className="grid gap-6">
      <p className="text-sm text-muted-foreground">
        Modifie les valeurs tarifaires utilisées par le moteur de calcul. Les
        devis déjà sauvegardés conservent leurs valeurs (snapshot figé).
      </p>
      {grouped.map((poste) => (
        <PosteSection
          key={poste.poste_numero}
          poste={poste}
          onValueChange={handleValueChange}
          onSavePoste={handleSavePoste}
          onResetPoste={handleResetPoste}
          editedValues={editedValues}
          isSaving={savingPoste === poste.poste_numero}
          isResetting={resettingPoste === poste.poste_numero}
        />
      ))}
    </div>
  );
}
