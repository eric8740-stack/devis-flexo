"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  decideControleBat,
  type DecideControleResponse,
} from "@/lib/api/controleBat";

interface DialogValiderProductionProps {
  controleId: number;
  devisNumero: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onValidated: (res: DecideControleResponse) => void;
}

/**
 * Sprint 15 Lot E — Dialog de validation de production par l'opérateur.
 *
 * Décision finale `valider` (le rejet n'a pas de bouton dédié dans le
 * brief Lot E ; si besoin, on ajoutera plus tard une variante depuis le
 * bandeau "Prévenir le chef d'atelier"). Capture le décideur (obligatoire,
 * traçabilité) et un motif optionnel (le brief précise « motif optionnel »).
 */
export function DialogValiderProduction({
  controleId,
  devisNumero,
  open,
  onOpenChange,
  onValidated,
}: DialogValiderProductionProps) {
  const [decideur, setDecideur] = useState("");
  const [motif, setMotif] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset à chaque ouverture/fermeture : pas de fuite d'état entre deux
  // validations, et l'erreur précédente ne reste pas visible à la ré-ouverture.
  useEffect(() => {
    if (!open) {
      setDecideur("");
      setMotif("");
      setSubmitting(false);
      setError(null);
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!decideur.trim()) {
      setError("Le nom du décideur est obligatoire pour la traçabilité.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await decideControleBat(controleId, {
        decision_finale: "valider",
        decideur: decideur.trim(),
        motif: motif.trim() || undefined,
      });
      onValidated(res);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Valider la production — {devisNumero}</DialogTitle>
          <DialogDescription>
            Vous confirmez que le 1er tirage est conforme et que la
            production peut continuer. Cette décision est tracée.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="grid gap-1.5">
            <Label htmlFor="decideur">Décideur (nom / initiales)</Label>
            <Input
              id="decideur"
              data-testid="decideur-input"
              value={decideur}
              onChange={(e) => setDecideur(e.target.value)}
              placeholder="Ex: J. Martin"
              autoComplete="off"
              disabled={submitting}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="motif">Motif (optionnel)</Label>
            <Input
              id="motif"
              data-testid="motif-input"
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              placeholder="Ex: Écart mineur de teinte accepté"
              autoComplete="off"
              disabled={submitting}
            />
          </div>
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Annuler
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="h-11 text-base"
          >
            {submitting ? "Enregistrement…" : "✅ Valider la production"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
